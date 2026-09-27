# Filler chunk c06 -- sealed five-sample pool of the current best SLURP system on 180 TRAIN Fold B rows

Registered before contact 2026-09-27 at study commit `bf483458` by `scripts/flights/filler/derive_filler_cells.py`; every cell **held**.
Owner decision 162: a standing filler family flown ONLY when the GPU would otherwise idle. DESCRIPTIVE:
an asset, never an admission cell. Family note: `docs/readiness/2026-09-27-slurp-stage3-filler-fold-b-family-v1/README.md`.

| file | what it holds |
|---|---|
| `../2026-09-27-slurp-stage3-filler-fold-b-c06-v1-preregistration.md` | the preregistration, with the `stage3_measurement` fence |
| `protocol-registered-v1.json` | identities, hashes, budgets, claim boundary |
| `registered-facts-v1.json` | the canonical `stage3_measurement` block, the roster, the prepared artifacts, the composed diff against ROLL-2 |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the arm's ExecutionPlan and FIT spend identity |
| `analysis-recipe-v1.json` | the sealed-pool read (ROLL-3's recipe against TRAIN gold) |
| `root-admission-draft-v1.json` | the DRAFT receipt root mints with `scripts/flights/filler/filler_mint.py` |
| `queue-step-v1.json` | the batch-driver step `scripts/flights/filler/batch_chain_filler.sh 6` writes |

**Numbers.** Arm: 180 rows, ceiling 19 per row, generation cap 3,420, FIT cap
13,680, repeated speech 9,744 s, GPU-hour cap
2.0, one official complete score. Expected about 1,499 contacts
and about 23.8 GPU-minutes at ROLL-2's measured rate.

**Flip and flight.** `filler_mint.py --chunks 6` (root) -> `filler_flip.sh 6` (root; loop form, one HEAD) ->
the idle-filler queue launches `batch_chain_filler.sh 6` when the card is idle. `--allow-output-change` must never
be passed. Read: `filler_pool_read.sh 6` after the seal and after the READ row `SAEA-SLURP-STAGE3-FILLER-FOLD-B-C06-READ-V1` is countersigned.
