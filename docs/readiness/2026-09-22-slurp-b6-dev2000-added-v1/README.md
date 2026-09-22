# Cell B6 -- DEV-2000-ADDED direct-vs-plan paired read

Registered before contact on 2026-09-22 by script
(`scripts/flights/derive_slurp_b6_dev2000_cells.py`) from two already-sealed precedents: the direct
max512 form (DEV-1000) and the locked v2.0 default plan (cell PLAN, TRAIN Fold A). Both forms fly
unmodified on the fresh DEV-2000-ADDED roster (1,000 rows, split identity `ee6c43cd4dd8fc2a583d2dd053e799c2d002efa3755fcd092ba7c7565431bf67`); only
the roster-bound bindings moved. No smoke: both forms are already sealed and flown elsewhere (see
`analysis-recipe-v1.json`'s `why_no_smoke`).

## Cells

| arm | run id | fit run id | baseline fragment | experiment fragment |
| --- | --- | --- | --- | --- |
| direct | `SAEA-SLURP-DIRECT-MAX512-DEV2000-ADDED-V1` | `SAEA-SLURP-DIRECT-MAX512-DEV2000-ADDED-FIT-V1` | `configs/baseline/slurp-direct-max512-dev2000-added-v1.json` | `configs/experiment/slurp-direct-max512-dev2000-added-v1.json` |
| plan | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1` | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-FIT-V1` | `configs/baseline/slurp-native-default-plan-dev2000-added-baseline-v1.json` | `configs/experiment/slurp-native-default-plan-dev2000-added-v1.json` |

Composed/protocol hashes at generation time (recomputed live by this script from the committed
fragments; a merge or re-pin that changes either fragment changes these, and this README along with
every other package file must be re-derived rather than hand-edited):

* direct: composed `b8e38d6ac04d9e5fc793af83d6bba7c58647f3470e49eec04cf0b98bb17e1f59`, protocol `281b9f3bdaf38a4164fdb796a0ccfa1d32f3002ca495e1b4dc24069a82b45cd1`
* plan: composed `b88f7b8285c9771a515ea378d6d8e53a5393694fedaae7fb6d9df8b4760d16bf`, protocol `e5e2ba6868f02a9b62ccfcd54ffe46a8e38f0bca5c4699f440bf95abbb40e93e`

## Readiness

Both cells stay `held`. Their `decision` readiness requirement carries a **placeholder sha256 of 64
zeros** at `coordination/slurp-b6-dev2000-added-v1/root-admission-v1.json` (decision id `slurp-b6-dev2000-added-admission-v1`): the coordinator mints that receipt on the
data root *after* this branch merges, then runs `scripts/flights/repin_cell.py` to re-pin the real hash,
flip readiness to `ready`, and -- for the plan arm only -- build and pin its own `prepared_phase_supply`
artifact model-free under its own run id (see `scripts/flights/repin.py`'s documented fallback for "a
cell registered before its supply could be prepared"). Neither cell carries a `prepared_phase_supply` pin
today, and this registration writes nothing under `$SPEECHRL_DATA_DIR` beyond the query-content
derivative of item 1 (`vectors/slurp-dev2000-added-v1/query-vectors-speech-content-v1.jsonl`, sha256
`7d4ebdce553fd897fa86cc6b6d878ebf2298e19ee509eeceaf1aa0aca4855ee0`, 1,000 rows).

## Re-deriving this package

`python scripts/flights/derive_slurp_b6_dev2000_cells.py` regenerates every file in this directory, the
sibling preregistration note and the five exposure-ledger rows from the committed baseline/experiment
fragments; it is idempotent (a re-run with no intervening edits is a no-op) and refuses to overwrite a
file whose on-disk content differs from what it would generate, or to touch an exposure-ledger row
already marked `consumed = yes`.

## Read

Paired, report-only: plan arm minus direct arm on the same 1,000 DEV-2000-ADDED rows. See
`analysis-recipe-v1.json` for the metrics, resampling and decision rule, and the sibling preregistration
note for the full statement. No admission verdict is read from this cell.
