# Cell B9a: acquisition on demand, kind (a) knowledge-requery (item E18), on the locked default-plan base: launch runbook

Preregistration: [`../2026-09-21-slurp-plan-acquisition-b9a-v1-preregistration.md`](../2026-09-21-slurp-plan-acquisition-b9a-v1-preregistration.md).
Owner decisions 43, 44, 78 (seal path); item E18.

## 0. In one paragraph

ONE factor: native_episode.acquisition armed with policy saea-acquire-knowledge-requery-v1 (kind (a): a model-free re-query of the released stores keyed by the Reviewer's findings, zero contacts) at budget max_acquisitions_per_row 1 / contact_budget 0, together with the optional fifth role roles.acquisition {phase_id acquisition, max_iterations 0, kinds [knowledge-requery]} that item E18 declares as one module (the loader refuses either half alone). The Planner may now route ACQUIRE once per row before its single revision; the contact ceiling stays 11 (the kind costs no contact). Everything else is the locked default plan byte for byte (cell PLAN's fragment).

## 1. What is registered here

Baselines `configs/baseline/slurp-native-plan-acquisition-b9a-baseline-v1.json` and `-smoke-4-baseline-v1.json`, experiment fragments
`configs/experiment/slurp-native-plan-acquisition-b9a-v1.json` / `slurp-native-plan-acquisition-b9a-smoke-4-v1.json`, campaign plan `configs/campaign/slurp-native-plan-acquisition-b9a-v1.json`, this package, four
exposure-ledger rows (`consumed = no`).

## 2. Mint, re-pin, flip, queue

Decision receipt `coordination/slurp-plan-acquisition-b9a-v1/root-admission-v1.json` minted by the coordinator; re-pin flips for the smoke and the arm; the flight commit pins the
batch worktree; the cell is queued behind PLANr on the SAEA-Batch-Driver scheduled task (decision 77). The read waits for the
PLAN and PLANr reads (comparator and margins).

## 3. What this package does not authorise

No flight before the receipt is minted and both cells are flipped; no contact by this registration; no re-flying of any
comparator; no kind (b) or (c); no test-split, Fold B or DEV-1000 read.
