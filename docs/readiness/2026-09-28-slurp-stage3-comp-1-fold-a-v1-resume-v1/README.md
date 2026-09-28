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
