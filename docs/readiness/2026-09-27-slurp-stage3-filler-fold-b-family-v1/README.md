# The standing rollout FILLER family on TRAIN Fold B (owner decision 162)

Registered before contact 2026-09-27 on branch `fable/filler` (base `5b536eac`). Six chunks registered, every
cell **held**; nothing here is minted, flipped, countersigned or flown. Authority: row 162 of
`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md` ("Agree to A; execute as recommended"), with
rows 77 (flights only through the batch-driver scheduled task), 101 (the Stage-3 label), 138-140 (throughput is a
first-class objective; no pre-committed if-then) and 161 (the agreement term is retained into COMP-1).

## What a filler chunk is

A sealed five-sample rollout pool of the **current best SLURP system** -- the locked PLAN plan plus the agreement
term (w_agree 1.0 over the self-excluded exemplar-intent vote, recall k 60, fuse 8-1-8) -- in cell ROLL-2's
grouped-Solver form (samples 5, temperature 0.7, the five registered seeds, plurality commit at min_support 3),
on 180 TRAIN rows. DESCRIPTIVE by construction (`stage3_measurement`: offline-sealed-pool, claims_benefit false;
the chunk-1 smoke form-proof), `stage3_algorithm` shared-rollout / rollout, never an admission cell. The pools are
the rollout substrate of the training-free RL inner loop (`sealed-credit-system-policy-v1`).

## The roster: TRAIN Fold B is the whole admissible universe

`docs/receipts/rosters/slurp-stage3-filler-fold-b-v1.json` (1,080 rows, split identity
`4407794c...a3484a`, identical ids to `slurp-evo-fold-b-v2.json`) with six chunk rosters `...-c01-v1` to
`...-c06-v1` (180 rows each, ten per scenario, seed 20260927) and the chunk-1 smoke roster (its first four rows).
Built by `scripts/flights/filler/build_filler_roster.py` (model-free, offline guard 0 attempts; `--check`
reproduces all eight receipts byte for byte). Proven before writing:

- **Universe.** The system's exemplar pool (`size-pool-annotated-exemplars`) holds 9,354 TRAIN utterances; with
  Fold A (1,080) and Fold B (1,080) that is all 11,514 SLURP TRAIN utterances, pairwise disjoint. The runner's
  BUILD/USE guard refuses a query row that is a knowledge source, so the ONLY TRAIN rows outside Fold A that the
  current best system can fly are Fold B's. **Six chunks exhaust the universe**; a seventh needs either a new
  system or a pool narrowed by a model-free release (the R01C / minus-R01 precedent), which is a new registration.
- **Knowledge sources.** Composite source ids (37,407 recordings over intent-boundaries 2,037, slot-contracts
  3,162, train-exemplars 37,407) share 0 recordings and 0 utterances with Fold B.
- **Evaluation rosters.** 0 shared recordings and 0 shared utterances with every SLURP receipt under
  `docs/receipts/rosters/` and `docs/receipts/probe-samples/` (51 receipts: DEV-2000-ADDED, DEV-2000, DEV-1000,
  the devel remainder v2 with its FINAL60 / probe-60 carve-outs, the test sample / closure / full, R01, R01C,
  Fold A, every Stage-3 subset, FINAL60, TRAIN90, ...), and with the governed devel (8,690) and test (13,078)
  enumerations. The parent's own superseded V1 draws (never contacted) are reported, not refused.

## The agreement table for the new rows

AGREE's table is keyed by Fold A sample ids, so the filler roster has its own:
`prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FILLER-FOLD-B-V1/agreement.jsonl` (sha256 `06990a86...21911`,
receipt `7e1bfe8b...1dc89`), built by the unchanged `scripts/build_slurp_intent_exemplar_agreement.py` from the
committed, never-flown FILLER BASE cell `slurp-native-stage3-filler-fold-b-base-v1` (ROLL-2 on the whole filler
roster at w_agree 0.0). Inputs, all already sealed: the Fold B speech-query encoding
(`SAEA-SLURP-TFRL-FOLD-B-SPEECH-QUERY-ENCODING-V1`), its model-free query-dimension alias, the Fold B
content-dimension derivative `vectors/slurp-stage3-filler-fold-b-v1/query-vectors-speech-content-v1.jsonl`
(`scripts/build_slurp_query_content_derivative.py`; byte-identical to the independently built
`vectors/slurp-system-update-fold-b-v1` file), the pool snapshot `4c498dc0...` and the boundary snapshot
`5520b844...`. Measured: 1,080 rows, every row 20 votes, 0 self-excluded exemplars, 0 rows without a vote, 60 of
60 boundary facets reachable. Zero model, server, encoder, embedder, scorer, network and GPU contacts. Ledger row
`SAEA-SLURP-STAGE3-FILLER-FOLD-B-PREPARE-V1` (model-free-check, DRAFT).

## The composed diff against ROLL-2

`scripts/flights/filler/derive_filler_cells.py` refuses unless every composed path that differs from cell ROLL-2
(arm, or smoke for the smoke) is (a) an agreement pin -- perception `k`, `rank_weights.w_agree`,
`agreement_source.*` -- equal to cell AGREE's, (b) a roster pin -- the two `query_source` pins, `population.*`,
`populations`, `split_id`, the `preparation_source_receipts` edits (Fold A alias -> Fold B alias, roster ->
chunk roster, + the Fold B encode receipt, the derivative's provenance and the agreement receipt) and the Fold B
dataset view -- or (c) run-id / budget / prose bookkeeping. `native_episode`, the policy program, prompts, stores,
releases, snapshots, scorers, geometry and packets are ROLL-2's byte for byte.
`tests/unit/test_filler_family.py` re-proves it from the committed files with its own implementation.

## Model-free proofs run at registration

- `build_filler_roster.py --check`: all eight roster receipts reproduce byte for byte.
- An in-memory build of chunk c01's first-phase Perception supply through the flight runtime's own seam
  (`build_flight_runtime` -> `phase_supply_artifact_identity` -> `build_supply_for_phase` ->
  `build_bootstrap_selection`, with the runtime's source-audio bindings; nothing written): 180 rows, the filler
  agreement table loaded (1,080 rows), eight boundary entries delivered on every row, and 145 of the 180 rows
  receive a different delivered boundary list than the same rows under the FILLER BASE's w_agree 0.0.
- `core.flight.cli check` at the registration commit: c01 and its smoke are **held**, sample counts 180 / 4,
  config and protocol hashes equal to the registered plans.

## Chunks, caps and time

| chunk | rows | generation cap | FIT cap | speech cap (s) | GPU-h cap | expected contacts | expected GPU-min |
|---|---|---|---|---|---|---|---|
| c01 smoke | 4 | 76 | 304 | 194 | 1.0 | 33 | 0.5 |
| c01 | 180 | 3,420 | 13,680 | 10,159 | 2.0 | 1,499 | 23.8 |
| c02 | 180 | 3,420 | 13,680 | 9,782 | 2.0 | 1,499 | 23.8 |
| c03 | 180 | 3,420 | 13,680 | 10,011 | 2.0 | 1,499 | 23.8 |
| c04 | 180 | 3,420 | 13,680 | 9,781 | 2.0 | 1,499 | 23.8 |
| c05 | 180 | 3,420 | 13,680 | 10,468 | 2.0 | 1,499 | 23.8 |
| c06 | 180 | 3,420 | 13,680 | 9,744 | 2.0 | 1,499 | 23.8 |

Expectations are ROLL-2's sealed arm on the same form: 8,996 contacts for 1,080 rows over 8,558 s of campaign
wall (8.33 contacts and 7.92 s per row at np4). The whole family is about 143 GPU-minutes (2.4 GPU-h) of
campaign wall plus about 1-2 minutes of driver overhead per chunk -- less than the 35 minutes per 200 rows the
decision estimated, because ROLL-2's measured wall is 26.4 minutes per 200 rows.

## Operating the family (root)

1. `python scripts/flights/filler/filler_mint.py --chunks 1-6 --countersign` -- mints the six receipts
   (`coordination/slurp-stage3-filler-fold-b-cKK-v1/root-admission-v1.json`) and countersigns the chunks' DRAFT
   ledger rows and the PREPARE row; commit `docs/exposure-ledger.md` on master.
2. `bash scripts/flights/filler/filler_flip.sh 1-6` -- loop-form flips (smoke then arm for c01), converging at
   ONE HEAD; final `core.flight.cli check` of every cell at that HEAD; writes
   `/home/chao/filler-flight-commit-cKK.txt`.
3. Copy `scripts/flights/filler/filler_queue.sh` to `/home/chao/saea-queue/` and register it as a Windows
   scheduled task (like `SAEA-Queue-*`). It launches ONLY when: no `batch-STOP` (else HALT), no
   `/home/chao/mainline-ready`, no flight / driver / lease process, no `locks/flight.lock`, no stale
   `batch-flight-repo.txt`, `batch-done` older than 300 s, and the np4 session resident, healthy, idle and
   sampled within 300 s. It then flies the lowest unflown, minted, flipped chunk through
   `batch_chain_filler.sh` and re-checks everything before the next one.
4. **Main-line protocol:** touch `/home/chao/mainline-ready` as soon as a main-line chain is flip-ready; the
   queue launches nothing while it exists, so the main line waits at most the one chunk in flight (about 24
   minutes). Remove it when the main-line chain has started. A main-line chain script started while a chunk
   flies refuses with exit 7 (its own guard); start it after the chunk's `batch-done`.
5. After each seal: register and countersign `SAEA-SLURP-STAGE3-FILLER-FOLD-B-CKK-READ-V1`, then
   `bash scripts/flights/filler/filler_pool_read.sh K` (ROLL-3's recipe against TRAIN gold).

## Things the coordinator should know

- **Fold B was also sketched as an evaluation roster** in the held, design-only memory-arm templates of
  `docs/readiness/2026-09-26-slurp-system-round-configs.md` ("Fold B E/M1/M2 evaluation"; not executable, not
  queued, no exposure authorization). Filler pools make Fold B a construction-exposed roster for the current
  system. It is already historically exposed TRAIN (EVO-S1 flights, the Fold B encoding), and no brief lists it
  as an evaluation roster, but if the memory arms are revived they need another roster.
- Only chunk 1 carries a four-row smoke: the composed form (ROLL-2 + AGREE) has never flown as one, and every
  later chunk is chunk 1's form on other rows.
- Development numbers only (owner decisions 28 and 86); TRAIN gold in the read; never a test claim.
