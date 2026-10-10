# Cell VER-1b: the three-sample greedy-first Solver pool on TRAIN Fold A, the confirmation pool of the VER-1 rule (owner decision 257, decision 258 option A) -- HELD

Registered 2026-10-10, before any contact, by `scripts/flights/ver/ver1b_derive_cells.py` and
`scripts/flights/ver/ver1b_write_registration.py`. HELD: nothing here authorises a flip, a flight or an admission entry. Decision 258
(option A: confirm on Fold A at n = 3) is PROPOSED, not ratified; this registration is the execution plan's "VER-1b Fold A confirmation
pool + a c3 column there" of decision 257, and the ledger rows are DRAFT until root countersigns them.

## What it is

The VER-1a pool read (`docs/readiness/2026-10-10-slurp-ver1a-samples-fold-b-v1/`) SELECTED the VER-1 rule on TRAIN Fold B: the support
filter over the Solver's own sampled answers at n = 3, s = 2, the c3 presence verdict gated by N1 >= 0.2, delivered through v4g
(filter + gate +1.29 / +1.43 in-sample, about +1.0 cross-fitted over the lock). VER-1b is the CONFIRMATION pool on the roster the rule
never saw:

* roster: `SLURP-EVO-FOLD-A-V2` (1,080 rows, `docs/receipts/rosters/slurp-evo-fold-a-v2.json`; the roster of the COMP-1b / A2 Fold A cells);
  tuning roster `SLURP-EVO-FOLD-B-V2`;
* base: the NX R5 composed arm / R6-P1 / VER-1a base -- the COMP-1b composition (agree-vote-seed + centroid-boundary-key ON) at lock v2.2,
  Reviewer loop OFF, no tool schema on any role, with the Fold A pins of the committed COMP-1b Fold A fragments;
* the ONE departure: the Solver visit is grouped at `samples = 3`. Sample 0 is GREEDY (`decoding_overrides.greedy_first`: the fragment's
  own temperature 0); samples 1-2 are drawn at temperature 0.7 (seeds `fragment_seed + seed_offset + index`);
* the in-flight delivered answer: `saea-commit-plurality-support-v1` at `min_support 2`, similarity 0.8 (the rule's own s);
* a POOL cell: `offline-sealed-pool`, expected effect 0.0 pp, `claims_benefit` false, stage-3 label `inference-time-verification-v1`
  (operators scoring, selection).

## The fixed rule (named in the facts and the preregistration)

n = 3, s = 2, theta = 0.2, base = sample 0 with its own labels, v4g at delivery, c3 verdict = the VER-1c `r1-c3` column answered no
entity after v4g. FIXED on the tuning roster `SLURP-EVO-FOLD-B-V2`; NOT re-tuned on Fold A. Nothing is selected on this roster. The
confirmation criterion is on file before the flight (in the decision rule of the protocol, plan and recipe): the rule's pooled SLU-F1
delta against the VER-1c lock column is at or above the 0.67 pp offline sealed-pool floor AND its CI95 lower bound is above zero AND
intent moves by no more than 0.67 pp; anything else is NOT CONFIRMED. Decision 258 may only tighten it.

## Why it is a hand-written fragment on a registered program id

Identical to VER-1a: `phase-native-module-v1-c4` is already a registered member of the review-off module program family
(`rails.controllers.MODULE_PROGRAM_FAMILY_IDS`; ceiling 1 + 1 x 3 = 4); the module compiler has no `samples` knob and the loader
verifies a declared `consumption_module` block against its own compilation, so the fragment declares none; `deliver_normaliser` is
refused beside a grouped Solver visit, so v4g is applied OFFLINE to every custodied raw sample and to the replayed commit. The derive
compiles the base block (the parent's own Fold A agreement and facet pins) to the R5 composed arm's policy blocks and changes exactly the
policy id, the module declaration, the delivery normaliser and the Solver `samples` / `decoding_overrides` / `commit`; the preflight
test proves the result equals the committed VER-1a Fold B fragment except for the Fold A pins and the sample parameters.

## Contact arithmetic

Per row: 1 Perception + 3 Solver = 4 (exact, no early exit). Arm: 1,080 x 4 = 4,320 generation calls; FIT 1,080 x 4 x 4 = 17,280
(structural); speech seconds `ceil(roster audio x 4)` = 12,339. Smoke: 4 x 4 = 16 calls; FIT 64. GPU hours planned 1.7 (arm; VER-1a
planned 2.5 for 6,480), 1.0 (smoke). The generation budget is run-cumulative across attempts; the FIT cap never is. The smoke
population is the first four Fold A rows (the COMP-1b Fold A smoke fragment's own ids).

## Identity-bound change (runtime)

`decoding_overrides.greedy_first` is already on master (VER-1a, `tests/unit/test_ver1a_greedy_first.py`); this cell adds no runtime
change.

## Order of operations (root)

countersign the four DRAFT flight rows (the READ row stays a draft until the seal) -> `scripts/flights/ver/ver1b_mint_receipt.py` ->
merge the engineering branch (no concurrent flip; no other experiment in flight) -> `scripts/flights/ver/ver1b_flip.sh` ->
`scripts/flights/refresh_registered_plan_pins.py` -> flip again -> `scripts/flights/ver/ver1b_dry_run.py` (root: needs the data root) ->
`scripts/flights/ver/ver1b_batch_chain.sh`. `--allow-output-change` must never be passed. The Fold A supply minted under this cell's run
id is expected to equal the COMP-1b Fold A digest; a different digest means the knowledge channel moved -- stop and report. VER-1b and
VER-1c are two cells with two receipts; the read needs both sealed (one experiment in flight: fly one, then the other).

## The combined read (VER-1b pool + VER-1c c3 column)

After both seals and both READ countersignatures:

```bash
python -B scripts/analysis/slurp_ver1_offline.py --mode read \
    --run-id SAEA-SLURP-STAGE3-VER1B-SAMPLES-FOLD-A-V1 --attempt attempt-slurp-native-stage3-ver1b-samples-fold-a-generation-v1 \
    --split train --rows 1080 --n 3 --s 2 --thetas 0.2 \
    --verdict-run SAEA-SLURP-STAGE3-VER1C-C3-COLUMN-FOLD-A-V1:attempt-slurp-native-stage3-ver1c-c3-column-fold-a-generation-v1:r1-c3 \
    --label VER1B-FOLD-A-V1 --sealed-scorer slurp-slu-official-train
```

The composer's `--verdict` option takes only the NX R1 iterations `i1,i2` (TRAIN Fold B); the generic `--verdict-run
RUN_ID:ATTEMPT:ARM[:KEY]` option was added for this read (commit "VER-1 offline composer accepts any sealed Solver template column as a
verdict source"; `i1,i2` keep working, the two options combine). It reads `runs/<VER-1c run>/<attempt>/supply-variants/arm-{lock,aa,r1-c3}-first-visit-outputs.jsonl`
and `arm-<arm>-slurp-slu-official-train-scores.json`, which VER-1c's READ recipe (`stage3_rollout_score.py --mode supply-variants`)
writes; N1 comes from that run's `phases.json`. The composer's `--n 3 --s 2 --thetas 0.2` restricts the report to the fixed rule
(the default s grid 2,3 and theta grid 0.1-0.9 would be a Fold A re-selection and must NOT be read as one). Outputs are write-once under
`$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-VER1-OFFLINE-VER1B-FOLD-A-V1/`.

## Open items

* The READ row has a recipe (`analysis-recipe-v1.json`) but no wrapper script yet; one is added at countersign time, cloned from
  `scripts/flights/roll2/roll2_pool_read.sh`.
* The confirmation criterion (floor + CI lower bound + intent) was written at registration; decision 258 is the owner's to tighten.
* Whether the greedy first sample reproduces the lock single-sample answer byte for byte is MEASURED in the read (stage 4), not assumed.
