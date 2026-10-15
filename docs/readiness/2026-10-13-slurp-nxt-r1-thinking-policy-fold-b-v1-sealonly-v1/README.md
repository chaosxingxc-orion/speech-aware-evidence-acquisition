# NX-T R1 seal-only completion of the stopped column flight

Registered 2026-10-15 by the engineering agent (Claude Sonnet 5.5, branch `sonnet/nxt1-sealonly`), model-free: zero model, tokenizer, encoder, scorer, server and GPU contact. Derived by
`scripts/flights/nx/nxt_r1_sealonly_derive_cell.py` (decision 58). The shape is the P-SV-1 seal-only completion (`docs/readiness/2026-09-29-slurp-stage3-psv1-fold-b-v1-resume-v1/`),
with two differences: the roster is NARROWED to the rows the stopped attempt completed, and the resume is mode A (trace) because the harness fix moves `rails/runner.py`.
**Not authorised by anything in this package.** The authority is the owner's answer to the coordinator's proposal (decision 320 A: seal-only the complete rows, read them, close the
cell), which was PENDING when this was written.

## What stopped

The column attempt `attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-rec1-v1` (run `SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-V1`, flight commit `8f9d8e1ee`, started 2026-10-14T17:14:43Z) stopped at 2026-10-15T22:33:00Z: `RailsRunnerError: perception branch 'both-off' sealed no level-2 Solver column`. Its attempt record reads
`ABORTED`, 10,298 calls, 30,101.2 s of repeated speech.

**Counts (corrected against the files).** 1,029 rows are complete in the trace AND in the row checkpoint (the same 1,029 ids); 1 row failed; the
other 50 were never started (1,029 + 1 + 50 = 1,080). The brief said
1,030 complete rows and 49 never flown: the 1,030th row is the FAILING one (10,298 contacts = 1,029 x 10 + 8; the checkpoint holds 1,029 row records). The failing row's emitted
trace records were never flushed (the trace buffer flushes a row after its episode settles); only its `sample-execution-timing` record (`status` failed, `error_type`
`RailsRunnerError`, `admission_index` 1,014 of 1,080, queue depth 16, 4 slots) reached the trace, so the failing row's own contact shapes cannot be read from the trace. The
root cause below rests on the campaign log (workflow events) and the contact arithmetic, and says so.

**Root cause (row class: a NON-delivering arm's no-think Solver hit its token cap).**

1. The first-visit Solver fan-out (`rails/runner.py` -> `reproduction/ojw/native_supply_variants.run_perception_branch_solver_arms`) invokes the five branches in declared
   order, `perception-off`, `solver-off`, `both-off`, `both-on-twin`, `both-on` (the delivering arm LAST).
2. In the failing row the THIRD Solver contact (`both-off`: `enable_thinking` false, `max_tokens` 1,024) ended on `finish_reason` `length`. The workflow log shows, for that
   workflow session, `graph_vertex_ability_error` on node `solver_0_role` with `metered completion is non-authoritative because finish_reason is 'length'` (2026-10-15 17:59:57 -04:00 = 21:59:57Z; the campaign then drained its in-flight rows and exited at 2026-10-15T22:33:00Z)
   after a 25 s request. `FrozenCoreRoleFiniteCompletionError` left the whole fan-out.
3. The row had made 8 contacts (5 Perception + 3 Solver), not 10; the twin and the delivering arm never ran, so **the delivering arm was NOT fine on that row** -- it was lost
   with the failing arm, because the fan-out is sequential and the delivering arm is last.
4. `reproduction/ojw/native_episode.py` took the row's `deliver-latest-or-abstain` disposition (the finite-completion policy), and the final assembly in `rails/runner.py` (the
   level-2 fold, `perception_branch_solver_records.pop`) found no Solver record for the first branch without one (`both-off`; `perception-off` and `solver-off` had theirs):
   `RailsRunnerError`. The campaign then drained its in-flight rows (they completed to 18:32 -04:00).
5. It was a first: across the 1,029 complete rows no no-think Solver contact came near the cap (2,058 `solver-off` / `both-off` Solver contacts, maximum completion 66 tokens, all
   `stop`); the Perception no-think contacts peaked at 116 tokens.

## The fix (merged with this package)

A finite completion on a branch that does NOT deliver is recorded as an ABSENT column and the fan-out continues, so the delivering arm still runs. The delivering arm keeps its
fail-closed path (a finite completion there still ends the row through the finite-completion policy). Receipt: two optional row keys `solver_absent` (true) and `absent_reason`
(`finite-completion:length` / `finite-completion:content_filter`), schema string unchanged, every old receipt verifies unchanged. The bundle (I7v) holds an absent mark against the
recorded wire `finish_reason`. The column renderer scores an absent column as the canonical empty answer (zero for that row's arm in every paired contrast); both NX-T readers print
`absent_rows` per arm and refuse a non-zero score for an absent row; the smoke sign-off conditions gain `absent_columns == 0`. The offline replay tool (the resume prelaunch gate's
checker) could not see the v5 thinking-policy wire check (all 1,029 rows failed it spuriously); it now carries each request's thinking decoding fields and each wire response's
finish_reason. Tests: `tests/unit/test_perception_branch_absent_solver.py`, `tests/unit/test_nxt_columns_absent_reader.py`.

## The completion

| field | value |
| --- | --- |
| experiment / cell | `slurp-native-stage3-nxt-r1-thinking-policy-fold-b-v1-sealonly` |
| baseline | `slurp-native-stage3-nxt-r1-thinking-policy-fold-b-baseline-v1-sealonly` (the parent's bytes except the FIT attempt id and the note) |
| dataset fragment / split | `slurp-speech-native-evo-fold-b-nxt1-complete-1029` / `SLURP-EVO-FOLD-B-V2-NXT1-COMPLETE-1029` (split identity `59b04947ab53819b59c8d1d70253196607c7bdb90514782183ab5198fc071a02`; a strict subset of `SLURP-EVO-FOLD-B-V2` `4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a`) |
| run id | `SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-V1` (the same run id) |
| attempt | `attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-rec1-sealonly-v1` (new) |
| FIT identity | `SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-FIT-REC1-V1` / `attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-fit-rec1-sealonly-v1` (fresh; it records no contact) |
| resume_from | `attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-rec1-v1`, trace `3238cd8aedb50c8a142b15e321070ffc7cf2cd055088fdcb0aee83d8a0895835`, 1,029 complete rows |
| checkpoint (corroboration) | `attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-rec1-v1` `.rows.ckpt.jsonl` sha256 `547b1fe24427f439d78d8b8f593a2d4807f51d5a38803757615efbdb25e45112` |
| allowed stages | `check`, `prepare-supply`, `seal-only` |
| program / arms | unchanged: `phase-native-module-v1-c10`, five arms |
| claim ceiling | `nominated`, `claims_benefit` false; `stage3_measurement` rows = 1,029 |

The union of the predecessor's complete rows covers the (narrowed) roster, so `core.flight.runtime` sets `is_seal_only`: zero new model contacts, no server, no slot, no lease.
Run-cumulative spend does not move (11,502 of 18,484 planned calls).

**Replay proof** (`resume_replay_proof` in the generation plan; model-free, on a scratch copy of the trace whose sha256 was verified identical): `replay_seal_consistency.py
--predecessor attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-rec1-v1:3238cd8a...` reported 1,029 rows checked, 0 failing, 0 sealed twice,
1,029 rows with perception branches, exit 0.

## Decisions this registration needs (flagged, not taken)

1. **Split identity.** The narrowed roster has its own split identity (`59b04947ab53...`), and one run id keeps one ledger row: root, when countersigning,
   replaces the arm rows' split-identity column with the subset's hash (the clause says so). If the owner prefers to keep the parent hash, the plan's split identity cannot
   agree with the loaded roster.
2. **`--allow-output-change` at the flip.** The rebuilt phase supply covers 1,029 rows, not 1,080; its output legitimately differs (the roster-narrowing precedent:
   `roll1_repin_arm.sh`). The seal-only path never reads the supply.
3. **Mode A, not mode B.** Mode B (checkpoint) refuses when `rails/runner.py` changed; the fix changes it. The checkpoint hash is recorded as corroboration.

## Sequence (the coordinator's; nothing below has been run)

1. Park the queue with `/home/chao/batch-STOP` while the cell is registered, countersigned and flipped (the flip refuses while a batch runs). Remove batch-STOP just before
   step 6: the seal-only chain REFUSES (exit 8) while it exists and never moves it aside.
2. Run the derive if the package is not committed yet: `python -B scripts/flights/nx/nxt_r1_sealonly_derive_cell.py --data-root $SPEECHRL_DATA_DIR --replay-json R --replay-commit C --replay-at T`.
3. Root countersigns `countersign-row-texts-v1.json` into `docs/exposure-ledger.md` (the two clauses, the proof row; the READ clause after the seal).
4. Mint: `python scripts/flights/nx/nxt_r1_sealonly_mint_receipt.py` (writes `coordination/slurp-nxt-r1-thinking-policy-fold-b-v1/root-admission-sealonly-v1.json` from `root-admission-sealonly-draft-v1.json`).
5. Flip: `bash scripts/flights/batch/flip_package_ext4.sh --flip "scripts/flights/nx/nxt_r1_sealonly_flip.sh" --package docs/readiness/2026-10-13-slurp-nxt-r1-thinking-policy-fold-b-v1-sealonly-v1 --cells slurp-native-stage3-nxt-r1-thinking-policy-fold-b-v1-sealonly --pins-commit-msg <file>`
   (loop form; writes `/home/chao/nxt1seal-flight-commit.txt`).
6. Chain: `bash scripts/flights/nx/batch_chain_nxt_r1_sealonly.sh` (one `seal-only` step through the batch driver; refuses while `batch-STOP` exists; the resume prelaunch gate
   runs first).
7. Read: `bash scripts/flights/nx/nxt_r1_read.sh sealonly-columns`, then (after the READ row's seal-only clause is countersigned) `bash scripts/flights/nx/nxt_r1_read.sh sealonly-read`.

## Rehearsal (already run; reproducible)

`replay_seal_consistency.py` needs the stopped trace (668 MB) on a scratch data root plus read-only symlinks to the live root's other entries (the v4g delivery normaliser reads
`prepared/` tables): `S=/home/chao/scratch-nxt1-seal; mkdir -p $S/runs/SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-V1/attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-rec1-v1; cp --reflink=auto $SPEECHRL_DATA_DIR/runs/SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-V1/attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-rec1-v1/SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-V1.trace.jsonl $S/runs/SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-V1/attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-rec1-v1/;
for e in $(ls $SPEECHRL_DATA_DIR); do [ "$e" = runs ] || ln -s $SPEECHRL_DATA_DIR/$e $S/$e; done; SPEECHRL_DATA_DIR=$S python -B scripts/analysis/replay_seal_consistency.py --experiment
slurp-native-stage3-nxt-r1-thinking-policy-fold-b-v1 --run-id SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-V1 --predecessor attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-rec1-v1:3238cd8aedb50c8a142b15e321070ffc7cf2cd055088fdcb0aee83d8a0895835 --data-root $S`. About 5 s, CPU only. The resume prelaunch gate (run by the chain) repeats it on the flight commit.

## Not verified here

`core.flight.cli` (check / seal-only), the re-pin tool with the narrowed supply, the batch driver's prelaunch and the sealed bundle's I7r verification were NOT run (no CLI, no
re-pin, no flip is allowed to this agent). What was run: unit tests, `flight_registration_check.py --cell`, `stage3_effect_floor_check.py`, the engineering gates, `compose` and
`compute_cell_identity` on the derived cell, and the offline replay on a scratch copy.
