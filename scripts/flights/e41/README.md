# scripts/flights/e41

Item E41 (owner decisions 103, 158): the mint / re-pin / flip scripts for the bounded-
Perception-note dry run and sub10 re-read (`e41_mint_receipt.py`, `e41_repin_dryrun.sh`,
`e41_flip_dryrun.sh`, `batch_chain_e41_dryrun.sh`, `e41_repin_sub10.sh`, `e41_flip_sub10.sh`,
`batch_chain_e41_sub10.sh`). The registration package itself, its README, and its recipes are
`docs/readiness/2026-09-27-e21-native-window-e41-v1/`.

## The dry-run READ driver

The dry run's own receipts-only read (`docs/readiness/2026-09-27-e21-native-window-e41-v1/
dry-run-analysis-recipe-v1.json`, recipe id `e21-native-window-e41-dry-run-receipts-read-v1`) is
implemented by `scripts/analysis/e21_e41_dry_run_read.py` -- the package README's step 5 named
this driver before it existed. It refuses unless the recipe's `read_run_id` row in
`docs/exposure-ledger.md` carries "root countersigned" and the sealed run manifest is
`COMPLETED`; reads only the recipe's named inputs (this arm's own trace and outputs, the sealed
E39b dry run's trace, and the sealed E35 four-row DIRECT arm's trace for the Perception note's
window-transcript re-emission feature); reuses `load_trace` and `note_features` from
`scripts/analysis/e21_e41_perception_note_trace_read.py` by import rather than copying them;
computes rules R1, R2 and R3 (R3 = the Perception truncation rate, target zero, with the Reviewer
truncation count reported beside it) and the recipe's tables and diagnostics; and writes
`read.json` / `read.md` (ids, counts, hashes, pass/fail only -- no utterance, transcript, gold or
model-output text) under `$SPEECHRL_DATA_DIR/analysis/
SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E41-V1-READ-V1/`. `--dry-run` validates the two
preconditions and prints trace/episode/contact counts only, writing nothing; it is the only mode
this driver may be run in against the real sealed run outside the coordinator's scheduled read.
Proofs: `tests/unit/test_e21_e41_dry_run_read.py` (synthetic fixtures only).
