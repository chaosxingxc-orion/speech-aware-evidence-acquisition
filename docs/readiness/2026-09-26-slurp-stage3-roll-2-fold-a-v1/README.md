# Stage-3 cell ROLL-2 -- the sealed five-sample pool on the v2.0 lock roster

Registered before contact 2026-09-26 at study commit `e0a8d20d`; both cells **held**. Nothing here
authorises a flight, a flip or an admission entry.

Cell ROLL-1's grouped-Solver form (samples 5, temperature 0.7, seed_offset 0, plurality commit at
min_support 3) on **TRAIN Fold A, 1,080 rows** -- the roster the v2.0 lock lives on. Zero factors
change; only the roster moves, and every roster-bound artifact takes the value the sealed Fold A
lock arm `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1` already flew.

**Why.** `docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md`: an action computable over a SEALED sample pool is read at about 0.67 pp at
n = 625 (about 0.51 pp at n = 1,080) at zero GPU cost, while a cross-flight contrast at this scale
carries a measured +1.87 pp A/A offset. The program has such a pool on R01C and **none** on the lock
roster, so no selection, commit, verification, projection or re-ranking policy can currently be
evaluated where the lock lives. This cell creates the pool. **DESCRIPTIVE: an asset, not a
comparison; no comparator, no gate, no admission claim.**

| file | what it holds |
|---|---|
| `../2026-09-26-slurp-stage3-roll-2-fold-a-v1-preregistration.md` | the preregistration proper, including the `stage3_measurement` fence |
| `protocol-registered-v1.json` | the registered protocol: identities, hashes, budgets, claim boundary |
| `registered-facts-v1.json` | every model-free measured fact, and the CANONICAL `stage3_measurement` block |
| `generation-plan-registered-v1.json` | the arm's `contracts.ExecutionPlan` as registered |
| `fit-plan-registered-v1.json` | the arm's FIT spend identity |
| `smoke-generation-plan-registered-v1.json` | the four-row smoke's plan |
| `smoke-fit-plan-registered-v1.json` | the four-row smoke's FIT spend identity |
| `analysis-recipe-v1.json` | how the sealed pool is read, offline, under its own later-registered read id |
| `dry-run-v1.md` | the offline four-row dry run: zero model, tokenizer, encoder, scorer and network contacts |

**Numbers.** Ceiling 19 = 1 + 2 x (1 x 5 + 3 + 1); generation cap 20,520 = 1,080 x 19; fit endpoint
cap 82,080 = 20,520 x 4; repeated speech 58,607 s = ceil(3084.5284375 x 19); GPU-hour cap 12.0; one
official complete score. Expected about 8.5504 contacts per row (cell ROLL-1's measured figure), so
about 9,234 contacts and about 3.5 GPU hours. Smoke: 76 / 304 / 202 s, no score.

**Flip and flight.** Root mints `coordination/slurp-stage3-roll-2-fold-a-v1/root-admission-v1.json` (id `slurp-stage3-roll-2-fold-a-admission-v1`) with the four eligible run ids, then
`scripts/flights/batch/roll2_flip_all.sh`; the flight is queued by
`scripts/flights/batch/batch_chain_roll2.sh` (one step, smoke then arm) and read by
`scripts/flights/batch/roll2_read.sh`. `--allow-output-change` must never be passed: this cell
carries no committed `prepared_phase_supply` and the flip mints its own.
