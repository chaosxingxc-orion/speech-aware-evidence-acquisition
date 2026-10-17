# NX-T R2 rec2 runbook (coordinator, on master after merging branch `sonnet/nxt2-rec2`)

Owner ruling 328 (2026-10-17): R2 continues as a RESUME of the aborted rec1 attempt. Nothing here has been run on master: no ledger append, no countersign, no
mint, no flip, no flight. All commands run in WSL `Ubuntu-24.04` from the master checkout (`cd /mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition`),
`source ~/.venvs/speechrl/bin/activate`, `export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD/src`, data root `/home/chao/saea-data/speechrl-data`.

What the branch registers (all computed from the data root, none typed): mode **A** (trace pin) because the launch-time checkpoint reader refuses the rec1 checkpoint for
any new attempt id (the protocol hash covers the cell's attempt id; the code identity itself is unchanged since `9790c071f`); the rec1 attempt keeps its complete rows
(the snapshot says how many) and the resume flies the rest; run-cumulative caps 11,880 + 42 + 172 = 12,094 calls and 35,317 speech-seconds; the GPU-hour ceiling is unchanged.

## Preconditions

1. NX-T R2b has sealed (exit rc 0) and no flight, lease or driver process is alive; `flight.lock` clear. Never register or start a serving or monitor task by hand (the swap does it).
2. The rec1 attempt directory under `runs/SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-V1/attempt-...-generation-rec1-v1/` is untouched (the chain re-hashes the pinned trace).

## Steps

1. Merge the branch (fast-forward or merge commit) with no other change on top.
2. Re-run the writer on master so the plans carry master's stamp and base commit, and append the two DRAFT rows (idempotent on the rec2 generation attempt id):
   `python -B scripts/flights/nx/nxt_r2_write_registration.py --study-commit 3b08bbd533a35d9726dd9be8019a98164fbacaff --recovery-registered-at <UTC, e.g. 2026-10-17T16:00:00Z> --recovery-base-commit $(git rev-parse --short HEAD) --append-recovery-ledger --data-root /home/chao/saea-data/speechrl-data`
   (`--study-commit` stays the ORIGINAL registration commit, as for rec1.) It re-verifies both snapshots against the data root (attempt records, trace and checkpoint hashes).
3. Countersign by hand in `docs/exposure-ledger.md`. The two rows whose notes start `REGISTERED (DRAFT, root countersignature pending)` are the rec2 generation row
   (`SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-V1`, block `## Cell NXT-R2 recovery rec2`) and `...-FIT-REC2-V1`: replace each row's notes with
   `countersign-row-texts-v1.json` `rows[<run id>]`, filling `<UTC timestamp>`. FOLD the rec1 generation row of the same run id (block `recovery rec1`, dated 2026-10-17T13:00:09Z)
   into the rec2 row: delete it (one run id, one row; the rec2 text names all earlier attempts and their spend). Leave the `...-FIT-REC1-V1` row and the READ row as they are.
4. Mint the receipt: `python scripts/flights/nx/nxt_r2_mint_receipt.py --dry --supersede`, then without `--dry`. The current receipt is renamed to
   `root-admission-v1.json.superseded-<UTC>-by-rec2.bak` (never deleted) and the new one lists the FIT-REC2 run id after the FIT-REC1 one. Commit the ledger, the package and the
   re-minted pins (`git commit -F <file>`).
5. Flip the arm cell only, after R2b's seal: `bash scripts/flights/batch/flip_package_ext4.sh --flip "scripts/flights/nx/nxt_r2_flip.sh" --package docs/readiness/2026-10-15-slurp-nxt-r2-thinking-budget-fold-b-v1 --cells slurp-native-stage3-nxt-r2-thinking-budget-fold-b-v1 --pins-commit-msg /home/chao/nxt2-pins-commit.txt -- NXT2_KINDS=arm`
   (never `--allow-output-change`; the sealed smoke is not touched). Read the gate block before trusting a converged-looking HEAD.
6. Hold the idle watchdog, then `bash scripts/flights/nx/batch_chain_nxt_r2.sh arm-only` (point `SAEA-Chain-NXT2` at it; the flight commit file is `/home/chao/nxt2-flight-commit.txt`, written by the flip).
   It checks the precondition, swaps to `think-budget-np4` if not resident, and the driver runs the resume prelaunch gate before the campaign opens.
7. After the seal: `bash scripts/flights/nx/nxt_r2_read.sh columns`, countersign the READ row, `bash scripts/flights/nx/nxt_r2_read.sh` (the read reports the kept / flown split). Close the ledger rows with `scripts/flights/batch/ledger_mark_consumed.py --apply`.

## What each refusal means

- Writer `mode B refused`: the rec2 input says `checkpoint` but the header binding fails; set `resume_mode` back via `nxt_r2_rec2_mode.py`. Writer `RecoveryError ... moved`: a snapshot no longer matches the data root (the predecessor is still spending, or a pinned file changed): stop and re-snapshot.
- Mint `not a strict prefix` / `decision ... expected`: the receipt on disk is not the rec1 one of this decision; `refusing to overwrite`: forgot `--supersede`. A refused mint restores the backup.
- Registration gate `[missing-row] ...FIT-REC2-V1`: step 2 not run on this tree. `resume-replay-unproven`: `resume-replay-proof-rec2-v1.json` missing from the plan (rerun the writer). `readiness`/pin findings: re-flip.
- Chain exit 9: the smoke is not sealed or the geometry differs; exit 5: no sign-off marker; exit 7: a batch or `flight.lock` is present; exit 6: serving swap failed OR the resume precondition failed. The precondition log (`/home/chao/batch-chain-nxt2.out`) names which: `predecessor trace pin moved`, `attempt record already exists`, `run directory holds more than the preflight declaration`, `declaration ... does not match`.
- Driver `resume replay gate REFUSED step N`: a kept row fails the seal re-render, a sample would be sealed twice, or the predecessor trace no longer hashes to the pin; the report is `/home/chao/batch-resumegate-<N>.out`. Do not retry blindly; this is the cell's last recovery (a failure of rec2 closes the cell).
