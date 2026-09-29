# Cell COMP-1 resume-recovery package (variant 1, HELD)

The registration note is
[`../2026-09-28-slurp-stage3-comp-1-fold-a-v1-resume-v1-preregistration.md`](../2026-09-28-slurp-stage3-comp-1-fold-a-v1-resume-v1-preregistration.md).
The parent package [`../2026-09-27-slurp-stage3-comp-1-fold-a-v1/`](../2026-09-27-slurp-stage3-comp-1-fold-a-v1/)
is never edited. Everything here was produced with zero model, tokenizer, encoder, scorer, server and GPU contacts.

| file | what it is |
| --- | --- |
| `README.md` | this runbook |
| `protocol-registered-v1.json` | the resume protocol: the parent protocol by reference, the abort, the decision-22 analysis, the proof, rows and budget |
| `generation-plan-registered-v1.json` | the registered generation plan of the resume attempt (same run id) |
| `fit-plan-registered-v1.json` | the registered FIT plan of the resume attempt (same FIT run id) |
| `analysis-recipe-v1.json` | the parent recipe with the arm's attempt moved to the resume attempt and the merged-manifest reading rule; READ run id unchanged |

## Recovery counter

COMP-1's **ONE** recovery re-registration. A second failure closes cell COMP-1.

## Launch sequence (after the owner rules for the resume)

1. Merge `fable/comp1rec` (the citation fix) and `fable/comp1res` (the resume-replay repair and this package).
2. Re-run the proof on the merged tree and confirm `verdict: PASS`:
   `PYTHONPATH=$MAIN/src python scripts/flights/comp1/comp1_resume_byte_identity_proof.py --repo-root $MAIN --data-root $DATA`.
3. Root countersigns the resume DRAFT clauses on the arm's generation and FIT rows and the proof row, marks the
   -REC section superseded unflown, and mints `coordination/slurp-stage3-comp1-fold-a-v1/root-admission-resume-v1.json`
   (decision id `slurp-stage3-comp1-fold-a-resume-admission-v1`; eligible: the arm run id and its FIT run id).
4. `bash scripts/flights/comp1/comp1_resume_flip.sh` -- loop form; converges the resume cell, G5 smoke and G5 arm at
   one HEAD and writes `/home/chao/comp1res-flight-commit.txt`. The re-pin rebuilds the inherited supply under the
   same run id and must reproduce output `ce68bebc...`; never `--allow-output-change`.
5. `bash scripts/flights/comp1/batch_chain_comp1_resume.sh` behind whatever occupies the np4 session.

Never write, move or compress anything under
`runs/SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1/attempt-slurp-native-stage3-comp1-fold-a-generation-v1/`: the resume
refuses before contact if its trace no longer hashes to `029a2dbb...61997`.

## Resume attempt 2 (2026-09-28)

Resume attempt 1 `attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume` (flight commit 902454db) aborted
at 2026-09-28T15:20:45Z on a server CUDA abort after 4 calls (llama-server `ggml_cuda_op_mul_mat_cublas` launch
failure three seconds after its first Perception wave; `RemoteDisconnected` -> ExecutionError 100054 ->
NativeEpisodeError); 10.56 s audio, 0 rows sealed; the resume loader and replay worked. It is retried as attempt 2
`attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume-2` under decision 22 (infrastructure, code
unchanged), `resume_from` still the ORIGINAL aborted attempt `attempt-slurp-native-stage3-comp1-fold-a-generation-v1`
(trace `029a2dbb...61997`; 471 kept, 609 flown). The one recovery of row 175 is unchanged: one recovery, retried
after an infrastructure abort. Attempt 1's 4 calls stay charged run-cumulatively (worst case 1,913 + 4 + 609 x 11 =
8,616 within 11,880). The FIT attempt id is unchanged (attempt 1 never reached FIT). The decision receipt is
re-minted as `coordination/slurp-stage3-comp1-fold-a-v1/root-admission-resume-v2.json` (same decision id,
`eligible_attempt_ids` naming attempt 2). Never write, move or compress anything under attempt 1's directory either.

## Resume attempt 3 (2026-09-29)

Resume attempt 2 `attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume-2` aborted at 2026-09-29T00:20:43Z on a FIT-identity collision (`native contact fit identity already has contact or result evidence`, `core/preparation_fit.py`) caused by a coordinator-side registration error: the FIT attempt id of attempt 1 (`attempt-slurp-native-stage3-comp1-fold-a-fit-v1-resume`) was reused, and attempt 1's per-contact FIT evidence already sat under `prepared/SAEA-SLURP-STAGE3-COMP1-FOLD-A-FIT-V1/` (the attempt-2 section above wrongly says attempt 1 never reached FIT). 48 calls / 119.3 s audio spent, no row sealed, no manifest; the 471 kept rows are untouched. Attempt 2's ABORTED record stays as it is.

Attempt 3 uses fresh generation and FIT attempt ids: `attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume-3` and `attempt-slurp-native-stage3-comp1-fold-a-fit-v1-resume-3`. `resume_from` is unchanged (the ORIGINAL aborted attempt, trace `029a2dbb...61997`; 471 kept, 609 flown). The one recovery of row 175 is unchanged. Run-cumulative spend on the arm before attempt 3 is 1,965 calls (1,913 + 4 + 48); worst case 1,965 + 609 x 11 = 8,664 within 11,880. The decision receipt is re-minted as `coordination/slurp-stage3-comp1-fold-a-v1/root-admission-resume-v3.json` (same decision id; eligible attempts attempt 3 and its dry run).

**The fix is proven on a 4-row dry run per row 181.** `core.flight.cli` has no bounded-resume mode (no row cap or dry-run flag for a resume), so the dry run is `SAEA-SLURP-STAGE3-COMP1-FOLD-A-RESUME3-SMOKE-4-V1` (FIT `SAEA-SLURP-STAGE3-COMP1-FOLD-A-RESUME3-SMOKE-4-FIT-V1`; attempts `attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume-3-smoke` / `attempt-slurp-native-stage3-comp1-fold-a-fit-v1-resume-3-smoke`): the parent COMP-1 smoke's bytes on its four rows under fresh ids, derived by `derive_slurp_comp1_recovery_cells.py --variant resume3-smoke`, re-pinned by `scripts/flights/comp1/comp1_repin_resume3_smoke.sh`. It flies through the same worker path and per-contact native FIT identity gate as the smoke of the resume step in `batch_chain_comp1_resume.sh`; the batch driver stops before attempt 3 opens unless the dry run passes its structural check. Form only.

## Seal-only completion (2026-09-29, owner decision 189 option A, PENDING)

Resume attempt 3 `attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume-3` flew all 609 remaining rows (2,476 calls, 7,392.9 s audio) and ABORTED at the seal:
`core.flight.resume._classify` replayed the raw recorded response for the 471 kept rows instead of the deliver
normaliser's output ("native delivery normalisation output differs from the delivered text"). Fixed at `d619e1c5`
(`fable/sealcheck`, merged); diagnosis and offline proof in the decision 181 addendum.

The seal-only completion is a new attempt `attempt-slurp-native-stage3-comp1-fold-a-generation-v1-seal-only` (FIT identity `attempt-slurp-native-stage3-comp1-fold-a-fit-v1-seal-only`, fresh) under the
same run id whose `resume_from` is a LIST:

| predecessor | trace sha256 | complete rows |
| --- | --- | --- |
| `attempt-slurp-native-stage3-comp1-fold-a-generation-v1` | `029a2dbb...` | 471 |
| `attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume-3` | `87be5cef...` | 609 |

The union covers the 1,080-row roster, so the runtime sets `is_seal_only`: zero new model contacts, no server, no slot,
no lease. `core.flight.cli seal-only` seals the merged manifest (I7r binds each kept row to its own predecessor trace)
and runs the one official finalize job. The cell allows `check`, `prepare-supply` and `seal-only` only; the old
single-cell campaign plan no longer loads for it.

**Replay proof** (`resume_replay_proof` in `generation-plan-registered-v1.json`, model-free, read-only):
`scripts/analysis/replay_seal_consistency.py` with both predecessors pinned, at `e4f4f588`: 1,080 rows checked
(471 + 609), 0 failing, 0 sealed twice; checker sha256 `5a90d298...`. The resume prelaunch gate gives the same counts.
Run-cumulative spend on the arm stays 4,441 calls (1,913 + 4 + 48 + 2,476) of 11,880; the completion adds none.

Sequence, only after the owner rules for option A:

1. Merge `fable/comp1seal` (it carries `fable/sealonly` and a master merge).
2. Root countersigns the DRAFT seal-only clauses on the arm's generation and FIT rows and the DRAFT row
   `SAEA-SLURP-STAGE3-COMP1-FOLD-A-SEALONLY-REPLAY-PROOF-V1`.
3. Root mints the receipt: `python scripts/flights/comp1/comp1_sealonly_mint_receipt.py` (writes
   `coordination/slurp-stage3-comp1-fold-a-v1/root-admission-sealonly-v1.json`, decision id `slurp-stage3-comp1-fold-a-sealonly-admission-v1`, eligible attempt `attempt-slurp-native-stage3-comp1-fold-a-generation-v1-seal-only`,
   declared 3.23 pp unchanged, superseding `root-admission-resume-v3.json`).
4. `bash scripts/flights/comp1/comp1_sealonly_flip.sh` -- loop form; converges the seal-only cell and G5's smoke and
   arm at one HEAD (runtime.py changed on `fable/sealonly`, so every prepared supply re-pins; never
   `--allow-output-change`) and writes `/home/chao/comp1seal-flight-commit.txt`.
5. `bash scripts/flights/comp1/batch_chain_comp1_sealonly.sh` when the np4 session is free: step 1 is the kind=seal-only
   step (no smoke), step 2 the G5 smoke and arm as before.

Never write, move or compress anything under either predecessor's attempt directory: the seal-only attempt refuses
before sealing if either trace no longer hashes to its pin.
