# Stage-3 cell ROLL-3 -- the sealed five-sample pool on the evaluation roster DEV-2000-ADDED

Registered before contact 2026-09-26 at study commit `66373032`; both cells **held**. Nothing here
authorises a flight, a flip or an admission entry.

Cell ROLL-2's grouped-Solver form (samples 5, temperature 0.7, seed_offset 0, plurality commit at
min_support 3; itself cell ROLL-1's) on **DEV-2000-ADDED, 1,000 rows** -- the evaluation roster where
every admitted policy must later be replicated. Zero factors change; only the roster moves, and every
roster-bound artifact takes the value the sealed DEV-2000-ADDED plan arm
`SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1` (cell B6, replicated by PLANr-DEV2000) already flew.
ROLL-3 is derived from ROLL-2's registration (`docs/readiness/2026-09-26-slurp-stage3-roll-2-fold-a-v1/`, pre-flip bytes at `7d49dc58`)
by re-pointing the roster and nothing else; the key list is `protocol-registered-v1.json` `what_moved`.

**Why.** `docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md`: an action computable over a SEALED sample pool is read at about 0.67 pp at
n = 625 (about 0.53 pp at n = 1,000) at zero GPU cost, while a cross-flight contrast at this scale
carries a measured +1.87 pp A/A offset. The program has such a pool on R01C and, since today, on TRAIN
Fold A -- and **none** on DEV-2000-ADDED, so no selection, commit, verification, projection or
re-ranking policy can be evaluated at that floor where it must later replicate (owner decisions 139 and
141 name ROLL-3 and dev sampling first). This cell creates the pool. **DESCRIPTIVE: an asset, not a
comparison; no comparator, no gate, no admission claim.**

| file | what it holds |
|---|---|
| `../2026-09-26-slurp-stage3-roll-3-dev2000-added-v1-preregistration.md` | the preregistration proper, including the `stage3_measurement` fence |
| `protocol-registered-v1.json` | the registered protocol: identities, hashes, budgets, claim boundary, the re-point key list |
| `registered-facts-v1.json` | every model-free measured fact, and the CANONICAL `stage3_measurement` block |
| `generation-plan-registered-v1.json` | the arm's `contracts.ExecutionPlan` as registered |
| `fit-plan-registered-v1.json` | the arm's FIT spend identity |
| `smoke-generation-plan-registered-v1.json` | the four-row smoke's plan |
| `smoke-fit-plan-registered-v1.json` | the four-row smoke's FIT spend identity |
| `analysis-recipe-v1.json` | how the sealed pool is read, offline, under its own later-registered read id |
| `dry-run-v1.md` | the offline four-row dry run and the pre-mint `check` of both cells: zero model, tokenizer, encoder, scorer and network contacts |

**Numbers.** Ceiling 19 = 1 + 2 x (1 x 5 + 3 + 1); generation cap 19,000 = 1,000 x 19; fit endpoint
cap 76,000 = 19,000 x 4; repeated speech 56,688 s = ceil(2983.52725 x 19); GPU-hour cap 11.2
(= ROLL-2's 12.0 x 1,000 / 1,080, rounded up); one official complete score. Expected about 8.5504
contacts per row (cell ROLL-1's measured figure; ROLL-2 flew 8.33), so about 8,550 contacts and
about 3.3 GPU hours. Smoke: 76 / 304 / 155 s / 1.0 GPU-h, no score.

**Roster.** `docs/receipts/rosters/slurp-dev-2000-added-v1.json` (`SLURP-DEV-2000-ADDED-V1`), split identity `ee6c43cd4dd8fc2a583d2dd053e799c2d002efa3755fcd092ba7c7565431bf67`, split role `dev`,
2983.52725 s of audio. The smoke flies its first four rows by roster order under split identity
`fee83441e514473dc4ab798f8554882bc5753c7fc4924eda0e72c7af7ed51ef0`, minted here through `data.splits.split_identity_hash` (no earlier smoke used them).

**Flip and flight.** Root mints `coordination/slurp-stage3-roll-3-dev2000-added-v1/root-admission-v1.json` (id `slurp-stage3-roll-3-dev2000-added-admission-v1`) with the four eligible run ids, then
`scripts/flights/batch/roll3_flip_all.sh`; the flight is queued by
`scripts/flights/batch/batch_chain_roll3.sh` (one step, smoke then arm) and read by
`scripts/flights/batch/roll3_read.sh`. `--allow-output-change` must never be passed: this cell
carries no committed `prepared_phase_supply` and the flip mints its own. `dry-run-v1.md` records the
PRE-FLIP run and quotes the smoke's composed hash exactly once; the coordinator re-runs
`roll3_dry_run.py` at the flipped bytes and rewrites that one line.
