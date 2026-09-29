# E4-1 seal-only completion (HELD; owner decision 194 pending)

Registered 2026-09-29 on master after the `fable/e4sealfix` merge, by the E4-1 seal-only registration agent
(Claude Opus 5.5). Model-free: no contact, no supply prepared, no receipt minted, no ledger row countersigned, nothing
flipped or sealed. Derived by `scripts/flights/e4/derive_slurp_e4_sealonly_cell.py` (decision 58). The shape is the
COMP-1 seal-only completion (owner decision 189 option A;
`docs/readiness/2026-09-28-slurp-stage3-comp-1-fold-a-v1-resume-v1/`).

## The abort

The E4-1 arm `SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-V1`, attempt `attempt-slurp-native-stage3-relisten-fold-a-generation-v1`,
flight commit `e9777e18`, flew all 1,080 rows of TRAIN Fold A (6,304 contacts, 18,730.5 s repeated speech; run_phases
complete 09:47:07Z-11:40:06Z) and ABORTED AT THE SEAL:

`FlightRuntimeError: finite source is not the last actual sample contact`
(`FlightRuntime.seal -> _merged_canonical_rows -> _canonical_output_rows`). No run manifest was written and nothing was
read. It was neither a serving death nor a cli-hazard STOP.

**Root cause.** 10 rows closed under the finite-completion policy (`deliver-latest-or-abstain`, item E13). On 8 of them
the post-accept relisten stage (owner decision 185; shadow delivery, so it never moves the delivered text) spent its
blind / forced-choice contacts AFTER the interrupted source contact. The seal compared the source with the sample's
last recorded contact, not with the last contact that can move delivery, so it refused a legal row. The four-row dry
run had no finite row, so it could not see this.

**Fix** (`fable/e4sealfix`, `b286d8974`, merged to master): the finite source must be the last contact that can move
delivery. Exactly the row's own `saea-relisten-v1` receipt contacts (`rails.relisten.relisten_contact_request_ids`), and
nothing else, may follow it, and every one of them must follow it. Without a receipt the check is unchanged. The resume
replay rebuilds the relisten receipt from the trace (`core.flight.resume.replay_relisten_receipt`), and
`scripts/analysis/replay_seal_consistency.py` runs I7l on relisten-armed rows. Regression test:
`tests/unit/test_e4_relisten_finite_seal.py`.

**Scratch rehearsal** (on a scratch copy of the attempt with the fixed code): 1,080 / 1,080 rows sealed, 0 abstained,
1,080 relisten receipts, 1,889 relisten contacts, contact total 6,304, equal to the trace. The sealed delivered-column
hash `81e977169486cd157e24280a7a65cd338c01217fb8ec9658a4eac0aa25277263` is identical to the live runtime-use custody.

## The completion

| field | value |
| --- | --- |
| experiment / cell | `slurp-native-stage3-relisten-fold-a-v1-resume` |
| baseline | `slurp-native-stage3-relisten-fold-a-baseline-v1-resume` (the parent's bytes except the FIT attempt id and the note) |
| run id | `SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-V1` (the same run id) |
| attempt | `attempt-slurp-native-stage3-relisten-fold-a-generation-v1-seal-only` (new) |
| FIT identity | `SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-FIT-V1` / `attempt-slurp-native-stage3-relisten-fold-a-fit-v1-seal-only` (fresh; it records no contact) |
| resume_from | `attempt-slurp-native-stage3-relisten-fold-a-generation-v1`, trace `966613e416dd81c9cd5bbdc21b16050f394844e5b9da6522ed8451b1f1f233f6`, 1,080 complete rows |
| allowed stages | `check`, `prepare-supply`, `seal-only` |
| readiness | `held` |
| roster / protocol / relisten program | the E4-1 arm's, unchanged (program `phase-native-candidates-review-revise-relisten-v1`, the same `native_episode.relisten` block) |
| claim ceiling | `nominated`, unchanged; `stage3_measurement` copied verbatim from the E4-1 package |

The union of the predecessor's complete rows covers the roster, so `core.flight.runtime` sets `is_seal_only`. That
means zero new model contacts, no server, no slot and no lease. `core.flight.cli seal-only` seals the 1,080-row manifest
(I7r binds every kept row to the predecessor trace) and runs the one official finalize job. Run-cumulative spend stays
6,304 calls of 18,360; the completion adds none. This is E4-1's ONE root-diagnosed recovery re-registration. A second
failure closes the cell.

**Replay proof** (`resume_replay_proof` in `generation-plan-registered-v1.json`; model-free and read-only over the REAL
attempt trace, at master `109538e8`): `scripts/analysis/replay_seal_consistency.py --predecessor
attempt-slurp-native-stage3-relisten-fold-a-generation-v1:966613e4...` reported 1,080 rows checked, 0 failing, 0 sealed
twice, 1,080 rows with a relisten receipt, exit 0. The resume prelaunch gate on this cell reports the same counts.

## Sequence (only after the owner admits it, decision 194)

1. Root countersigns the DRAFT seal-only clauses on the arm's generation and FIT rows, plus the DRAFT row
   `SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-SEALONLY-REPLAY-PROOF-V1`.
2. Root mints the receipt with `python scripts/flights/e4/e4_sealonly_mint_receipt.py`. It writes
   `coordination/slurp-stage3-relisten-fold-a-v1/root-admission-sealonly-v1.json` from
   `root-admission-sealonly-draft-v1.json`, with decision id `slurp-stage3-relisten-fold-a-sealonly-admission-v1`.
3. `bash scripts/flights/e4/e4_sealonly_flip.sh` is loop form. `runtime.py` changed with the seal fix, so the inherited
   supply pin re-pins, and its output must stay `eab5c61e...`. Never pass `--allow-output-change`. The script writes
   `/home/chao/e4seal-flight-commit.txt`.
4. Run `bash scripts/flights/e4/batch_chain_e4_sealonly.sh` when no batch is running. It has one kind=seal-only step
   with no smoke and no campaign plan.
5. The column read runs by the unchanged READ row `SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-COLUMN-READ-V1` over the seal-only
   attempt's manifest (`analysis-recipe-v1.json` here). That row is countersigned before any column score is opened.
