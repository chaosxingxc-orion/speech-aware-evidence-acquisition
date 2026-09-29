# P-SV-1 seal-only completion (owner decision 197)

Registered 2026-09-29 on master after the `fable/psvsealfix` merge (`0177f83fc`), by the ops agent (Claude Opus 5.5,
single master writer). Owner decision 197 admits the completion. Model-free: no contact. Derived by
`scripts/flights/psv/derive_slurp_psv1_sealonly_cell.py` (decision 58). The shape is the E4-1 seal-only completion
(owner decision 194; `docs/readiness/2026-09-29-slurp-stage3-e4-relisten-fold-a-v1-resume-v1/`), which followed the
COMP-1 seal-only completion (owner decision 189 option A).

## The abort

The P-SV-1 arm `SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1`, attempt `attempt-slurp-native-stage3-psv1-fold-b-generation-v1`,
flight commit `b9af3e58`, flew all 1,080 rows of TRAIN Fold B (8,709 contacts, 25,428.7 s repeated speech; run_phases
complete). It then ABORTED AT THE SEAL at 2026-09-29T14:19:36Z on the seal invariant I7v:

`BundleError: outputs row <row id> (request flight-0183): perception-branch receipt is invalid: perception branch
candidate_intent_ids must be a non-empty ordered list of distinct non-empty strings (I7v)`

No run manifest was written and nothing was read. It was neither a serving death nor a cli-hazard STOP. The flight lock
was reconciled by `scripts/flights/batch/lease_reconcile_psv1.sh`
(`coordination/slurp-stage3-psv1-fold-b-v1/flight-lock-reconciliation-20260929T143300Z.json`).

**Root cause.** The runner sealed each Perception branch note's candidate intent list verbatim. 61 notes over 49 rows
listed one intent twice: a-agree 21, b-top2contrast 17, t-twin 23. I7v requires a list of distinct intents, so the seal
refused rows whose branch notes were legal measured outcomes. The four-row smoke had no such row, so it could not see
this.

**Fix** (`fable/psvsealfix`, `6fb31f8d3`, merged at `0177f83fc`):

- Receipt schema `saea-perception-branch-arms-v2`. `candidate_intent_ids` collapses duplicates, keeping the first
  occurrence. `candidate_intent_ids_raw_count` records the raw length. `note_parse_status` is one of `ok`,
  `duplicates-collapsed`, `empty` or `malformed`.
- One shared parser (`native_episode_receipt.parse_perception_branch_note`) serves the runner, the resume replay and the
  bundle.
- The level-2 fold carries `presentation_skip_reason`, `contrast_block_sha256` and `min_candidates_met` through.
- The resume replay rebuilds the branch block from the trace (`replay_perception_branch_block`).
- The bundle's I7v re-derives the note fields from the trace.
- The branch read treats `empty` / `malformed` as gold-absent.
- Regression tests are in `tests/unit/test_perception_branch_degenerate_lists.py`.

**Scratch rehearsal** (on a scratch copy of the attempt with the fixed code): 1,080 complete, 0 incomplete, 0 failing
rows. The delivered columns are identical to the live outputs (delivered-column hash `1f05aee5...` on both sides). The
b-top2contrast presentation outcome is 1,035 rendered, 42 `insufficient-pool-support` and 3
`fewer-than-two-candidates`.

## The completion

| field | value |
| --- | --- |
| experiment / cell | `slurp-native-stage3-psv1-fold-b-v1-resume` |
| baseline | `slurp-native-stage3-psv1-fold-b-baseline-v1-resume` (the parent's bytes except the FIT attempt id and the note) |
| run id | `SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1` (the same run id) |
| attempt | `attempt-slurp-native-stage3-psv1-fold-b-generation-v1-seal-only` (new) |
| FIT identity | `SAEA-SLURP-STAGE3-PSV1-FOLD-B-FIT-V1` / `attempt-slurp-native-stage3-psv1-fold-b-fit-v1-seal-only` (fresh; it records no contact) |
| resume_from | `attempt-slurp-native-stage3-psv1-fold-b-generation-v1`, trace `0c1edb20c37756ec8567fbba8edc56d8ff24ce3ea32b94bccad8c3667285d20a`, 1,080 complete rows |
| allowed stages | `check`, `prepare-supply`, `seal-only` |
| roster / protocol / branch program | the P-SV-1 arm's, unchanged (program `phase-native-candidates-review-revise-pbranch3-l2-v1`, the same level-2 branch block) |
| claim ceiling | `nominated`, unchanged; `stage3_measurement` copied from the P-SV-1 package with `primary_metric_key: "intent"` added (decision 190) |

The union of the predecessor's complete rows covers the roster, so `core.flight.runtime` sets `is_seal_only`. That
means zero new model contacts, no server, no slot and no lease. `core.flight.cli seal-only` seals the 1,080-row manifest
(I7r binds every kept row to the predecessor trace) and runs the one official finalize job. Run-cumulative spend stays
8,709 calls of 16,200; the completion adds none. The arm's exposure-ledger rows stay `consumed = no` (the abort never
closed them). This is P-SV-1's ONE root-diagnosed recovery re-registration. A second failure closes the cell.

**Replay proof** (`resume_replay_proof` in `generation-plan-registered-v1.json`; model-free and read-only over the REAL
attempt trace, at master `0177f83fc`): `scripts/analysis/replay_seal_consistency.py --predecessor
attempt-slurp-native-stage3-psv1-fold-b-generation-v1:0c1edb20...` reported 1,080 rows checked, 0 failing, 0 sealed
twice, 1,080 rows with perception branches, exit 0. Note parse status per branch: a-agree 1,059 ok / 21
duplicates-collapsed; b-top2contrast 1,063 ok / 17 duplicates-collapsed; t-twin 1,057 ok / 23 duplicates-collapsed.

## Sequence (owner decision 197)

1. Root (act delegated by decision 197) countersigns the seal-only clauses on the arm's generation and FIT rows, plus
   the row `SAEA-SLURP-STAGE3-PSV1-FOLD-B-SEALONLY-REPLAY-PROOF-V1`.
2. Root mints the receipt with `python scripts/flights/psv/psv1_sealonly_mint_receipt.py`. It writes
   `coordination/slurp-stage3-psv1-fold-b-v1/root-admission-sealonly-v1.json` from
   `root-admission-sealonly-draft-v1.json`, with decision id `slurp-stage3-psv1-fold-b-sealonly-admission-v1`.
3. `bash scripts/flights/psv/psv1_sealonly_flip.sh` is loop form. The rails implementation hashes changed with the fix,
   so the inherited supply pin re-pins, and its output must stay `81d6a712...`. Never pass `--allow-output-change`. The
   script writes `/home/chao/psv1seal-flight-commit.txt`.
4. Run `bash scripts/flights/psv/batch_chain_psv1_sealonly.sh` when no batch is running. It has one kind=seal-only step
   with no smoke and no campaign plan.
5. The branch read runs by the unchanged READ row `SAEA-SLURP-STAGE3-PSV1-FOLD-B-BRANCH-READ-V1` over the seal-only
   attempt's manifest (`analysis-recipe-v1.json` here). That row is countersigned before any branch column is opened.
