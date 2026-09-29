# Cell COMP-1 recovery, variant 1: RESUME-RECOVERY of the aborted arm (HELD)

Status: **REGISTERED BEFORE CONTACT, HELD until the owner rules between this resume and the -REC
re-registration** (`2026-09-28-slurp-stage3-comp-1-fold-a-rec-v1-preregistration.md`). The variant the
owner does not choose is superseded unflown. Written with zero model, tokenizer, encoder, scorer,
server and GPU contacts. No utterance text, transcript, gold label or model output is printed or
persisted anywhere in this package: ids, counts and hashes only.

This note addends the COMP-1 registration
[`2026-09-27-slurp-stage3-comp-1-fold-a-v1/`](2026-09-27-slurp-stage3-comp-1-fold-a-v1/) and its
preregistration, which are **not edited**. Everything they fix -- the question, the composition, the
comparator, the decision rule, the margins, the declared expected effect (3.23 pp intent), the
attribution table and the prohibitions -- stands unchanged and is not re-litigated.

## 1. What aborted

The arm attempt `attempt-slurp-native-stage3-comp1-fold-a-generation-v1` of run
`SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1` ABORTED on 2026-09-28 at contact `flight-1854`, flight commit
`cb628f59`: 471 rows settled, 1 row incomplete, 608 rows never started, 1,913 contacts, 5,171.38 s of
repeated speech. The trace is 10,035 records, SHA-256
`029a2dbbd62bc8752ff9e7d6a53dfee0cb49872f48b11267e49c4022c9561997`. Root cause, named to a component
(`docs/results/2026-09-28-slurp-comp1-citation-abort-diagnosis.md`):
`rails.solver_citation.parse_cited_answer` refused a repeated intent citation id that the per-contact
grammar legally admits. The fix is `a451f942` (`rails/solver_citation.py` only, outside the prepared
identity set). The shared in-chain A/A `SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1` FINALIZED and was scored
before the arm opened; **it is never re-flown**.

## 2. The resume cell

| item | value |
| --- | --- |
| experiment / cell | `slurp-native-stage3-comp1-fold-a-v1-resume` |
| run id | `SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1` -- **unchanged; this is what a resume is** |
| generation attempt | `attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume-3` (attempt 3, 2026-09-29; attempt 1 `attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume` ABORTED 2026-09-28T15:20:45Z on a server CUDA abort after 4 calls; attempt 2 `attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume-2` ABORTED 2026-09-29T00:20:43Z on a FIT-identity collision caused by a coordinator-side registration error -- it reused attempt 1's FIT attempt id; 48 calls / 119.3 s spent) |
| FIT run / attempt | `SAEA-SLURP-STAGE3-COMP1-FOLD-A-FIT-V1` (unchanged) / `attempt-slurp-native-stage3-comp1-fold-a-fit-v1-resume-3` (fresh; `attempt-slurp-native-stage3-comp1-fold-a-fit-v1-resume` holds attempt 1's and attempt 2's per-contact FIT evidence and is never reused) |
| `resume_from` | `{"attempt_id": "attempt-slurp-native-stage3-comp1-fold-a-generation-v1", "trace_sha256": "029a2dbb...61997"}` |
| baseline | `configs/baseline/slurp-native-stage3-comp1-fold-a-baseline-v1-resume.json` (the arm's, except the FIT attempt id and the note) |
| campaign plan | `configs/campaign/slurp-native-stage3-comp1-fold-a-v1-resume.json` (the resume cell only) |
| rows | 471 kept under I7r custody without selection; 609 flown (1 partial + 608 unstarted) |
| budget | run-cumulative: 1,913 spent + 609 x 11 = 6,699 worst case = 8,612 within 11,880 (3,268 headroom) |
| prepared supply | inherited from the arm (`phase-supply-v3.json`); the flip rebuilds it and asserts output `ce68bebc...` unchanged |
| readiness | `held`; decision `slurp-stage3-comp1-fold-a-resume-admission-v1`, receipt `coordination/slurp-stage3-comp1-fold-a-v1/root-admission-resume-v1.json` -- **root mints it** |
| derivation | `scripts/flights/comp1/derive_slurp_comp1_recovery_cells.py --variant resume` |

**The recovery counter.** This is COMP-1's **ONE** root-diagnosed recovery re-registration. A second
failure CLOSES cell COMP-1: no third registration, and the fix must be proven on a four-row dry run
before another mechanism is admitted.

## 3. Owner decision 22, and why the owner must rule

`core/flight/resume.py` states decision 22's rule: a resume-recovery "applies ONLY when the code and
the request bytes are unchanged -- an infrastructure failure (the resident server was killed, the host
rebooted), never a harness or config defect". The arm's own `failure_policy` repeats it: the resume
form applies "if the abort is an INFRASTRUCTURE failure with code and request bytes unchanged ...;
otherwise the one recovery is a full re-fly". **By the letter, this abort does not qualify**: it was a
harness defect, and two harness files changed:

1. `rails/solver_citation.py` (`a451f942`): a repeated citation id is collapsed and counted instead of
   refused;
2. `core/flight/resume.py` (`49f88ce6`, this branch): the replay no longer claims the `context_fit` and
   `solver_citations` receipt blocks as wire contacts (`NON_WIRE_CONTACT_BLOCKS`). **Without this repair
   the resume keeps nothing**: every settled row of this cell read "the episode receipt names contact
   None" (0 of 471 COMPLETE, measured on the real trace), so the recovery would re-fly all 1,080 rows
   under the same run id, whose run-cumulative worst case (1,913 + 11,880) exceeds the 11,880 cap. The
   diagnosis note's "471 COMPLETE in the core.flight.resume sense" held only after this repair. The
   repair skips the two blocks by name; any other contacts array is still claimed, and a wire contact
   naming an unrecorded request still refuses its row (`tests/unit/test_flight_resume_recovery.py`).

**The purpose of the rule is proven model-free** by
`scripts/flights/comp1/comp1_resume_byte_identity_proof.py`, whose receipt is
`$SPEECHRL_DATA_DIR/coordination/slurp-stage3-comp1-fold-a-v1/resume-byte-identity-proof-v1.json`
(re-runnable; it re-hashes the trace, reads the predecessor code with `git show cb628f59:...`):

| check | result |
| --- | --- |
| trace SHA-256 equals the declared `029a2dbb...` | yes |
| rows COMPLETE / INCOMPLETE / never started | 471 / 1 / 608 |
| cited Solver contacts in the trace | 482 |
| captures (state bytes, cited ids, record) identical under the predecessor and the fixed code | 481 of 481 |
| kept-row sealed citation records byte-identical to the fixed code's record | 481 of 481 |
| refused by the predecessor, sealed by the fix | 1 (`flight-1854`; `duplicate_citation_ids_dropped` 2; in the one INCOMPLETE row, which is re-flown) |
| regressions / grammar re-render mismatches | 0 / 0 |

So the request bytes are unchanged (every per-contact grammar re-renders from its own supplied ids),
every kept row's custody is exactly what the recovery tree writes, and the one changed disposition is
confined to a row the resume re-flies. **Whether that admits a resume is the owner's ruling.**

**No commit-equality rule exists.** Neither `core/flight/resume.py`, the runtime's resume path
(`runtime.py` `_load_resume_predecessor`, ~1614-1719) nor `core.bundle.verify_bundle` compares the
recovery's flight commit with the aborted attempt's. The runtime refuses only a missing or re-hashed
predecessor trace, a predecessor that flew rows outside the roster, a non-native dispatch, an
execution-unit roster or an artifact result, and a recovery that reuses the aborted attempt id. The
merged manifest's `study_commit` is the recovery flight commit, and I7r verifies each kept row
against the predecessor trace by sample id and bytes.

## 4. What remains untested before contact

The replay classification and the citation records are proven on the real trace. The rendering of
the 471 kept rows through `_canonical_output_rows` and the bundle verifier's I7r pass over a merged
manifest whose rows carry `context_fit` and `solver_citations` blocks are exercised only by the
synthetic unit harness, not by this cell's real bytes; the first real exercise is the flight itself.
A refusal there happens at seal, after the 609 rows are spent.

## 5. The ledger

The resume flies under the arm's own run id, so it adds no flight row: a DRAFT clause is appended to
the arm's generation and FIT rows (precedent B8b-anchor), and one model-free row
`SAEA-SLURP-STAGE3-COMP1-FOLD-A-RESUME-BYTE-IDENTITY-PROOF-V1` records the proof, citing decision 22 and
the receipt. The READ row `SAEA-SLURP-STAGE3-COMP1-FOLD-A-PAIRED-ANALYSIS-V1` is unchanged. Both arm
rows must still read `consumed = no` at launch.

## 6. The flight

G5 never started in the aborted chain: no `runs/` or `attempts/` directory exists under
`SAEA-SLURP-STAGE3-G5-FOLD-A-V1` or its smoke (verified 2026-09-28; only its prepared supplies
`phase-supply-v1/v2.json` exist). The chain `scripts/flights/comp1/batch_chain_comp1_resume.sh` flies
ONE queue of two steps: the resume cell (kind `resume`, no smoke), then the G5 smoke and arm exactly as
`batch_chain_comp1_g5.sh` had them. Both arms are read at the shared A/A. **Disclosed:** that A/A flew
in the aborted chain; the resumed rows and G5 fly in a later chain, so "in-chain" now holds for the
471 kept rows only. The declared design is not re-declared.

Flip: `bash scripts/flights/comp1/comp1_resume_flip.sh` (loop form; refuses until the proof passes, the
receipt is minted, the A/A is FINALIZED, G5 is unstarted and both arm rows read `consumed = no`).
Launch: `bash scripts/flights/comp1/batch_chain_comp1_resume.sh`.

## 7. Seal-only completion (2026-09-29; owner decision 189 option A, PENDING)

Resume attempt 3 flew all 609 remaining rows and aborted at the seal on a replay defect in
`core.flight.resume._classify`, fixed at `d619e1c5`. Under option A of decision 189 the recovery completes WITHOUT any
new model contact: attempt `attempt-slurp-native-stage3-comp1-fold-a-generation-v1-seal-only` declares `resume_from` as the ordered list
[`attempt-slurp-native-stage3-comp1-fold-a-generation-v1` (trace `029a2dbb...`, 471 complete rows), `attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume-3` (trace `87be5cef...`,
609 complete rows)], whose union is the whole 1,080-row roster, so the runtime seals the merged manifest and nothing is
flown. The FIT identity is fresh (`attempt-slurp-native-stage3-comp1-fold-a-fit-v1-seal-only`) and records no contact.

The replay proof is registered before the seal: `scripts/analysis/replay_seal_consistency.py`, both predecessors pinned,
1,080 rows checked, 0 failing, 0 sealed twice (checker sha256 `5a90d298...`, code commit `e4f4f588`). The comparator,
the READ row `SAEA-SLURP-STAGE3-COMP1-FOLD-A-PAIRED-ANALYSIS-V1`, the declared 3.23 pp and every rule above are unchanged.
This is still the one recovery of row 175: if the seal-only completion fails, cell COMP-1 closes.

Flip: `bash scripts/flights/comp1/comp1_sealonly_flip.sh`. Launch: `bash scripts/flights/comp1/batch_chain_comp1_sealonly.sh`.
