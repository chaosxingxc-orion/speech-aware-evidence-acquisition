# The standing rollout FILLER family (owner decision 162)

Sealed five-sample rollout pools of the current best SLURP system on TRAIN rows outside Fold A, every
evaluation roster and every knowledge source, in chunks of about 200 rows, flown ONLY when the GPU would
otherwise idle. Family note: `docs/readiness/2026-09-27-slurp-stage3-filler-fold-b-family-v1/README.md`.

| file | role | who runs it |
|---|---|---|
| `filler_family.py` | shared identities, budgets, the derivation and the composed-diff rule | imported |
| `build_filler_roster.py` | freezes the family roster, its chunk rosters and the chunk-1 smoke roster (model-free) | registration agent |
| `derive_filler_cells.py` | `--base` writes the never-flown FILLER BASE; `--chunks 1-6` writes each chunk's configs, readiness package and DRAFT ledger rows | registration agent |
| `filler_mint.py --chunks 1-6` | mints the chunks' root-admission receipts on the data root; `--countersign` rewrites their DRAFT ledger rows | root |
| `filler_flip.sh 1-6` | flips a batch of chunks in loop form, converging at ONE HEAD (the batch's flight commit) | root |
| `filler_repin_cell.sh` | per-cell environment for `scripts/flights/batch/repin_cell_generic.sh` | called by the flip |
| `batch_chain_filler.sh <k>` | flies chunk k through the batch driver (mirrors `batch_chain_roll2.sh`) | the queue |
| `filler_queue.sh` | the idle-filler queue: launches the next unflown, minted, flipped chunk only when the card is idle and no main-line chain is ready | Windows scheduled task |
| `filler_queue_decide.py` | the queue's decision function (tested) | called by the queue |
| `filler_pool_read.sh <k>` | chunk k's sealed-pool read (ROLL-3's recipe against TRAIN gold) | coordinator, after the seal and the READ row |
