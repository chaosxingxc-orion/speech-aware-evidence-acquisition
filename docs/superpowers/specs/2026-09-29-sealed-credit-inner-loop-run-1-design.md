# Sealed-credit inner loop, run 1 (design)

Date 2026-09-29. Carrier SLURP only (owner decision 187). Algorithm `sealed-credit-system-policy-v1`
(`core/stage3_algorithms.py`, status `planned`; owner decisions 101, 165, 172, 180). This note is
model-free: it registers no cell, authorises no flight and claims no effect. Every number quoted is a
TRAIN or DEV development number (owner decisions 28 and 86).

## 1. Inventory

### 1a. Exists as code

| module / function | what it computes | what it reads |
| --- | --- | --- |
| `core/stage3_algorithms.py` `SEALED_CREDIT_SYSTEM_POLICY_V1` | the registry record only: six operators, four departures (typed update, credit over deliberate variants, selection inside the policy, re-execution admitted only above the floor) | nothing (label resolution for `stage3_algorithm_label_check.py`) |
| `scripts/analysis/stage3_rollout_score.py` (`--mode grouped / supply-variants / perception-branches / relisten`) | per-sample or per-column official scores on derived copies; `per_row.json`, `pairs.json` with a trajectory block (Perception ids, gold-in-candidates boolean, Reviewer/Planner labels) | sealed `outputs.jsonl`, episode receipts, `trace.jsonl`, roster |
| `scripts/analysis/slurp_node_gain_ledger.py` `derive_arm`, `intent_ledger`, `slot_ledger` | per-row node states (B, P, K, S1, R, D) and per-item slot classes; edge gains with bootstrap | two hard-coded single-sample Fold A arms (AGREE, wave A/A); sealed phases, outputs, scores; gold offline |
| `scripts/analysis/slurp_agree_arm_error_sources.py` `entity_items` | the entity item taxonomy (EXACT / FORMAT / BOUNDARY / NEAR / WRONG-VALUE / WRONG-TYPE / MISSING / SPURIOUS) | delivered answer plus gold |
| `scripts/analysis/slurp_reviewer_credit_table.py` | the one node-scoped inner loop that ran: per-visit Reviewer credit by pre-review class, gate x scope grid, two-fold cross-fitted selection by utterance on R01C pools only, `SLU_GUARD_PP = -0.10` | 22 sealed pools (its `POOLS` tuple) |
| `analysis/citation_credit.py` | per-entry supplied / cited / cited-correct table | sealed `cited_value_ids` (only where `solver_citation` is armed) |
| `analysis/deliver_normaliser_replay.py`, `analysis/native_commit_replay.py` | offline re-application of a normaliser or commit policy | sealed `outputs.jsonl` |
| `scripts/analysis/slurp_sample_aggregation_offline_read.py` | 29 commit rules over 5 samples; pooled reconstruction from count fields | ROLL-1 score root |
| `rails/supply_variants.py` `SUPPLY_VARIANT_KNOB_TAILS` | closed same-flight knobs: `phase_supply.k`, `fuse_coverage.{m,c,top_l}`, `candidate_supply.max_candidates`, release swap | fragments |
| `rails/relisten.py` | E4 contacts; receipt `saea-relisten-v1` (per entity: blind disposition, value hashes, confirm choice, accept bit) | runtime |
| `scripts/checks/stage3_effect_floor_check.py` `FLOOR_TABLE` | floor per design (0.67 offline at 625; 0.735 at 200 same-flight; cross-flight bar 3.0 at 625, 2.5 at 1,080) | preregistrations |
| `scripts/checks/flight_registration_check.py` (item D3) | `tuning_roster` / `read_roster`, `tuning-read-overlap` | roster receipts |
| `slurp_w4/w5_fold_a_offline_estimate.py`, `rankvis_probe_read.py`, `slurp_conv_probe_read.py` | expected pp = items newly shown x measured conversion; targeted conversion rates | one arm each |

### 1b. Described only in prose

- The loop as a whole (instrument note section 5; re-plan v2 section 3).
- Departure (i), the typed update: no data type names a policy as a set of knob values.
- Departure (ii), credit over deliberate variants: VAR-1 and W-SV-1 are such variants; no code pools them.
- Departure (iv), the acceptance test: enforced per cell by the floor check; no code compares a candidate's
  predicted effect with its read design's floor.
- The expected-gain calculus: by hand per cell (REV-TFRL-1's 1.697 x 0.1417 / 0.3000; W5's 0.2471).
- One entity taxonomy as the registered credit surface (re-plan v2 section 3).

### 1c. Missing to run one full pass

A pool manifest validated against the D3 roster receipts; a row-state extractor for every pool kind (the
ledger's `derive_arm` is two-arm, single-sample, Fold A only); a persisted per-node credit table; a closed
policy-space document naming each knob's estimator and conversion source; a composed-policy estimator
that repairs a row at most once; the acceptance step (design, floor, ranking, one nomination); the CLI
with a byte-reproducibility check.

## 2. The first run

### 2a. Inputs (pools)

| pool | run id | roster (n) | kind | scorer sibling for per-sample scores | use in run 1 |
| --- | --- | --- | --- | --- | --- |
| ROLL-1 | `SAEA-SLURP-STAGE3-ROLLOUT-R01-V1` | R01C (625) | grouped 5, locked PLAN | `slurp-slu-official-projected-v3-train` | tuning |
| VAR-1 family, ROLL-AA, candrec | the `selection` rows of the credit driver's `POOLS` | R01C (625 each) | single-sample deliberate variants (k 10 / 30, diversity, Perception k16c5) with PLANR | sealed `scores.json` (`-train` sibling) | tuning |
| ROLL-2 | `SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-V1` | Fold A (1,080) | grouped 5, PLAN + agreement term | `slurp-slu-official-projected-v3-train` (sealed delivered commit: unprojected `slurp-slu-official-train`, beside only) | tuning |
| Fold A single-sample arms | AGREE, wave A/A, W1, W3a, W4, REV-TFRL-1 (+ its A/A), RANKVIS (119 targeted rows), W-SV-1 columns once read | Fold A | single sample; W-SV-1 same-flight columns | sealed `scores.json` and W-SV-1 columns: `slurp-slu-official-train` | tuning |
| filler c01-c02 (c03-c06 later) | `SAEA-SLURP-STAGE3-FILLER-FOLD-B-C0k-V1` | Fold B chunks (180 each) | grouped 5 | `slurp-slu-official-projected-v3-train` | descriptive only (section 3) |
| ROLL-3 | `SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-V1` | DEV-2000-ADDED (1,000) | grouped 5 | `slurp-slu-official-projected-v3` (DEVEL gold) | never tuning; read-roster null only |

Per row the run reads: per-sample official count fields (from the score roots, pooled by
`pooled_from_sums`), the trajectory block and episode receipt (Perception candidate ids in order, Solver
sample indices and answer hashes, Reviewer verdicts, Planner routes, revision count, delivery kind), and
the gold side offline (intent, entity items) through the governed loaders only.

### 2b. Credit surface

Per row, the ledger's node states: gold position in the boundary block; gold Perception rank (1 / 2 /
3+ / absent) and list size; exemplar-vote position of gold (top / outvoted / zero); Solver first answer
correct and on-list; Reviewer route and change (none / intent / entities, toward or away from gold);
normaliser change (label / entities); delivered correctness. For grouped pools S1 becomes five samples
plus the commit, and the normaliser node is absent. Per gold entity item: the eight-class taxonomy at
S1, R and D, the Perception-note state (CONTIGUOUS / NEAR / PARTIAL / ABSENT) and the knowledge state
(gold value printed / other type / not printed).

A node state's credit is P(delivered correct | state) with a whole-utterance cluster-bootstrap
interval; a node's credit is the net rows its edge moves. On Fold A (AGREE): gold at Perception rank 1 converts at 97.57 %, rank 2 at
26.98 % (63 rows), rank 3+ at 12.0 %, absent at 2.35 %; the Solver adds 0 net intent rows, the
Reviewer/Planner -1, the normaliser +21.

### 2c. Policy space

| knob | node | values searched | estimator in run 1 | conversion source |
| --- | --- | --- | --- | --- |
| `phase_supply.k` | Solver supply | 10, 20 (as flown), 30 | conversion estimate | VAR-1 EX-K10 / EX-K30 vs PLANR; W-SV-1 columns when read |
| `phase_supply.fuse_coverage.{m,c,top_l}` | Solver supply | as flown, one step each | conversion estimate | none sealed; W-SV family |
| release swap (slot contracts) | Solver supply | locked, `slot-contracts-w4-v1` | conversion estimate | W4 read (+0.79 SLU [-0.56, +2.12]); W4-SV columns when read |
| `candidate_supply.max_candidates` | Solver candidate supply | as flown, one step | conversion estimate | none sealed |
| boundary `phase_supply.{k, fuse_coverage}` | Perception seed | as flown (8 entries), one step | conversion estimate | ledger block-position conversions (gold at block 4-8: 12 of 49 delivered) |
| `rank_weights.w_agree` | Perception seed | 1.0 (flown), 0.0 | conversion estimate | AGREE vs PLAN pools (circular on Fold A; section 3) |
| `presentation_id` | Perception | none, `rank-visible-v1`, `top2-contrast-v1` | conversion estimate | RANKVIS m = 19 of 119 vs 15.9 no-op; CONV 32 of 70 |
| `min_candidates` | Perception contract | as flown, 3 | conversion estimate | ledger: 49 wrong rows with gold in the block but off the list; rank-3 conversion 12.0 % (P-SV-2 ceiling about 6 rows) |
| relisten acceptance | post-accept | off, replace-only, replace + drop-when-unheard | conversion estimate from the ledger's 142 BOUNDARY / NEAR / FORMAT items | none sealed (E4-1) |
| Reviewer / Planner | review loop | on, off | exact offline (deliver S1) | every single-sample pool |
| deliver normaliser | delivery | on, off | exact offline (`deliver_normaliser_replay`) | every pool |
| commit rule | grouped Solver | none | excluded | commit line closed (0 of 29 rules; C11) and multi-sample rule designs discontinued (decision 179) |

A composed policy is one value per knob. The expected gain of a knob value is the sum, over the
credit-surface classes it acts on, of (rows or items in that class) x (conversion under the value minus
conversion under the flown value) / n, bootstrapped jointly over rows and over the conversion rate's own
interval. Composition assigns each row to at most one repairing node, by flight order (Perception, then
Solver supply, then Reviewer, then relisten, then normaliser), so a row repaired upstream is removed from
every downstream class. Knob values with no sealed conversion source enter with an expected gain of 0.0
and a flag `unobserved`; they may be carried in a composed policy only as no-harm passengers.

### 2d. Objective (as the code and the readiness text state it)

No single objective function exists in code. Stated: registry record (iv), "an update is ADMITTED TO
RE-EXECUTION only when its predicted effect exceeds the measured floor of the design that would read it",
and the GPU is re-entered "for the composed policy and its in-chain replicate"; the node-scoped instance
(`slurp_reviewer_credit_table.py`) keeps a candidate only if its mean SLU-F1 delta on the choosing fold is
not below `SLU_GUARD_PP = -0.10`, intent primary, two-fold cross-fit by utterance on selection pools only;
instrument law rule 3 admits cross-flight only with the CI95 lower bound above zero and the delta above
the in-chain replicate's offset plus its half-width (about 2.5 pp at 1,080).

Run 1 therefore maximises expected intent gain, subject to expected SLU-F1 gain >= -0.10 pp on both
cross-fit folds, and admits a candidate to re-execution only if its expected gain exceeds the floor of
its read design. Two designs apply: the same-flight twin null at n = 1,080, 0.735 x sqrt(200 / 1,080) =
0.3163 pp SLU (0.000 intent, the W-SV-1 package's provisional floor), for a policy the instrument can
carry as one column; the cross-flight bar 2.5 pp at 1,080 for any policy it cannot. The offline floor is
not 0.67 for multi-sample pools: decision 179 records the measured DEV multi-sample offline null of
1.547 pp SLU / 0.810 intent, so offline differences between rules over grouped pools are not reads.

### 2e. Output

`candidates.json`: a ranked list (top 20) of composed policies, each with its knob values, expected
intent and SLU-F1 gain (point and 95 % interval), the classes and row counts it acts on, the read design,
that design's null (0.3163 same-flight at 1,080 or the 2.5 cross-flight bar), a boolean `clears_floor`,
and the conversion sources' run ids and content hashes. Only the top candidate that clears its floor
becomes a cell, with claim ceiling `nominated`; a same-flight read cannot admit (the instrument spec's Q6 ruling). If no
candidate clears, the run nominates nothing and says so. Counts, rates, ids and hashes only.

## 3. Leakage rules

- **Split (recommended).** Tuning roster = R01C + TRAIN Fold A (ROLL-1, VAR-1, ROLL-2, the Fold A arms).
  Read roster = TRAIN Fold B (same-flight, n = 1,080), then DEV-2000-ADDED for admission (cross-flight
  with its in-chain A/A). The filler pools are Fold B rollouts; under decision 186 a policy built from
  Fold B rollouts may not be read on Fold B, so in this split the filler enters only as the read roster's
  descriptive baseline and within-pool null, never as a conversion source. ROLL-3 never enters tuning.
- The alternative (filler in tuning, read on DEV only) is question Q1.
- TRAIN-only construction (released, hash-pinned TRAIN-derived stores and alternates); no gold at
  runtime; gold is read offline on the scoring side only.
- The nominated cell registers `stage3_measurement.tuning_roster` (R01C, Fold A) and `read_roster`
  (Fold B or DEV); `flight_registration_check.py` must report no `tuning-read-overlap`.
- `w_agree` was tuned on Fold A gold (item D3's circular read): conversions from AGREE versus PLAN on
  Fold A are flagged `circular-source`.
- The CLI refuses a read roster among tuning pools, a DEV pool marked tuning, or a missing roster receipt.

## 4. What run 1 cannot see

- **Undetermined slot items.** 229 of AGREE's 407 delivered slot errors are "undetermined": the
  Perception note is an intent note and is silent on them, so no node state separates hearing from
  consumption there. Run 1 credits no knob with them; relisten estimates use only the 142 BOUNDARY /
  NEAR / FORMAT items and their note states.
- **Perception-side variants.** Every sealed pool varies the Solver (temperature, or supply k on R01C);
  none varies Perception. Its knobs are estimated from targeted probes (RANKVIS 119 rows, CONV 70 rows)
  whose rows were selected wrong-first, so their conversion does not transfer to a whole roster without
  a reach term; run 1 reports them with that caveat and at most `nominated`.
- **Temperature spread is thin.** One intent across all five samples on 93.5 % (ROLL-2) and 90.5 %
  (ROLL-3) of rows: grouped pools carry little credit on the intent decision.
- **Run 2 inputs.** P-SV-1 / P-SV-2 perception-branch columns (scored by `--mode perception-branches`),
  E4-1's relisten receipts (alternative acceptance rules then become exact recomputations over one
  flight) and the W-SV-1 / W4-SV supply columns enter as deliberate-variant pools (departure ii) and
  replace the matching `conversion estimate` rows. P-SV is on Fold B, so nothing built from it is read on
  Fold B (decision 186).

## 5. Implementation plan

Each task is one Sonnet-sized, model-free change in a worktree, tested on synthetic sealed rows (no real
utterances in fixtures). Package `src/speech_aware_evidence_acquisition/analysis/sealed_credit/`.

1. **Pools.** `configs/analysis/sealed-credit-pools-v1.json` + `pools.py` (kind, scorer sibling, roster
   receipt, use; reuse the D3 overlap reader). `tests/unit/test_sealed_credit_pools.py`: overlap,
   DEV-as-tuning and missing-receipt refusals.
2. **Row states.** `row_states.py`: lift `derive_arm`, `note_state`, `gold_item_states` and
   `entity_items` out of the ledger and error-source scripts (both then import them; their `--check`
   stays byte-equal); add grouped pools. `tests/unit/test_sealed_credit_row_states.py`.
3. **Credit.** `credit.py`: conversion per node state (cluster bootstrap), per-edge net rows, per-item
   classes; canonical JSON with `table_sha256`. Test order independence and byte reproducibility.
4. **Policy space.** `configs/analysis/sealed-credit-policy-space-v1.json` + `policy_space.py`: validate
   paths against `SUPPLY_VARIANT_KNOB_TAILS`, the phase-2 axes and the relisten modes; each value names
   its estimator and source. Test unknown-path and non-tuning-source refusals.
5. **Estimator.** `estimate.py`: single-knob gain; exhaustive composition with flight-order precedence;
   two-fold cross-fit by utterance; SLU guard -0.10. Test on a surface with a closed-form answer.
6. **Acceptance.** `accept.py`: design assignment, floors (`FLOOR_TABLE`, the 0.3163 twin null, the
   decision-179 null), ranking, one nomination. Test nominate / none clears / tie.
7. **CLI.** `scripts/analysis/sealed_credit_inner_loop.py`:

   ```
   sealed_credit_inner_loop.py --pools configs/analysis/sealed-credit-pools-v1.json
       --policy-space configs/analysis/sealed-credit-policy-space-v1.json
       --data-root "$SPEECHRL_DATA_DIR" --lock <umbrella datasets.lock.json>
       --out "$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-SEALED-CREDIT-INNER-LOOP-RUN-1-V1"
       [--check] [--workers 8]
   ```

   Writes `row-states.jsonl` (ids, ranks, classes, booleans), `credit.json`, `candidates.json`,
   `report.md`, `content-sha256.json`; refuses a non-empty `--out` without `--check`; zero model, server,
   GPU and scorer contacts (existing score roots only). End-to-end test on a synthetic data root.
8. **Registration.** A model-free read row, countersigned before any number is read; result note under
   `docs/results/`.

## 6. Open questions for the coordinator

- **Q1. Split.** Recommended: tune on R01C + Fold A, read on Fold B then DEV, filler descriptive only.
  Or put the filler into tuning and read on DEV only (more tuning rows, one read roster)?
- **Q2. Objective.** Confirm "intent primary, SLU guard -0.10 pp on both folds, expected gain above the
  read design's floor" as the locked objective, or name a joint score.
- **Q3. Decision 179.** Offline rule designs on multi-sample pools are discontinued. Run 1 uses the grouped
  pools only as credit surface and conversion sources, never to read a rule. Is that inside the ruling?
- **Q4. Composition.** The same-flight instrument carries one Solver-supply or one Perception-branch
  column. A composed policy spanning both needs the cross-flight 2.5 pp bar. Accept that, or restrict
  run 1's search to what one column can carry?
- **Q5. Probe transfer.** May RANKVIS / CONV conversions, which were measured on wrong-first targeted
  rows, source Perception estimates in run 1? Or must Perception knobs wait for P-SV (run 2)?
- **Q6. Status.** Does the registry record move from `planned` to `base-loop` after run 1 lands, or
  only after the first nominated cell flies?

## Coordinator rulings (Fable 5.1, 2026-09-29)

Answering section 6's open questions, before implementation.

- **Q1 (split).** Tune on R01C (ROLL-1, the VAR-1 family) plus Fold A (ROLL-2, the single-sample
  arms); read on Fold B (same-flight) then DEV-2000-ADDED for admission. The filler pools stay out of
  tuning (decision 186); ROLL-3 never tunes.
- **Q2 (objective).** Intent primary. The SLU guard is the READ DESIGN'S OWN NULL (the twin null for
  same-flight, the in-chain A/A null for cross-flight) -- not the flat `-0.10` pp `slurp_reviewer_
  credit_table.py` uses for its own, separate inner loop. Candidates are ranked by predicted intent
  gain; a candidate is discarded if its predicted SLU change is below minus the guard. A candidate is
  nominated only if its predicted effect exceeds the floor of the design that will read it.
- **Q3 (decision 179).** Yes, inside the ruling: grouped multi-sample pools RANK candidates only (as
  a credit surface and, where a pool pair permits, a conversion source); no offline read over them is
  a verdict.
- **Q4 (composition).** Run 1 is restricted to policies one same-flight column can carry -- one node
  changed per candidate. Combined Perception+Solver policies are deferred to run 2 (after the P-SV
  pools) unless their predicted effect exceeds 2.5 pp (the cross-flight bar at n = 1,080).
- **Q5 (probe transfer).** RANKVIS/CONV/KPROBE probe rates may enter only as bounds, with the
  selection caveat (wrong-first targeted rows; no reach term) stated per candidate. Perception knobs
  are otherwise deferred to run 2.
- **Q6 (status).** The algorithm's status moves from `planned` to `base-loop` when run 1's nominated
  cell has flown and been read (the loop closed once) -- not merely when run 1's own model-free pass
  lands.

Implementation of these rulings: `src/speech_aware_evidence_acquisition/analysis/sealed_credit/`
(`pools.py`, `row_states.py`, `credit.py`, `policy_space.py`, `estimate.py`, `accept.py`),
`scripts/analysis/sealed_credit_inner_loop.py`, `configs/analysis/sealed-credit-pools-v1.json`,
`configs/analysis/sealed-credit-policy-space-v1.json`. Run 1's own read (same-flight-supply-variant,
model-free) is reported under `docs/results/`; no cell is registered by this pass.
