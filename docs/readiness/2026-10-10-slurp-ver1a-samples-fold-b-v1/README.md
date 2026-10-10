# Cell VER-1a: the five-sample greedy-first Solver pool on TRAIN Fold B (owner decision 257) -- HELD

**AMENDED 2026-10-10 to 5 samples before any contact** (coordinator ruling after the offline composer read; nothing flown). The cell was
first registered at three samples (program c4, min_support 2, 4 contacts per row, 4,320 calls). The offline composer
(`scripts/analysis/slurp_ver1_offline.py`, `docs/readiness/2026-10-10-slurp-ver1-offline-composer-v1/README.md`) resolves the support filter's
gain over v4g only at n = 5, s = 2 (ROLL-2 Fold A +1.03 [+0.47, +1.70]; ROLL-3 DEV +0.76 [+0.08, +1.45]) and not at n = 3 (+0.91
[-0.07, +2.03] / +0.18 [-0.71, +1.06]), so the pool carries five samples and s = 2, 3-of-5 and the gate combination can all be read
offline. The four countersigned flight rows were amended in place (countersignature text verbatim); the decision receipt must be re-minted.

Registered 2026-10-10, before any contact, by `scripts/flights/ver/ver1a_derive_cells.py` and
`scripts/flights/ver/ver1a_write_registration.py`. HELD: nothing here authorises a flip, a flight or an admission entry.

## What it is

The verification layer (VER-1) of the training-free RL round needs the Solver's OWN sampled answers on the roster where the c3 verdict
columns already exist (TRAIN Fold B, `SLURP-EVO-FOLD-B-V2`, 1,080 rows; the NX R1 / R6 flights). VER-1a seals that sample pool:

* base: the NX R5 composed arm / R6-P1 base -- the COMP-1b composition (agree-vote-seed + centroid-boundary-key ON) at lock v2.2,
  Reviewer loop OFF, no tool schema on any role;
* the ONE departure: the Solver visit is grouped at `samples = 5`. Sample 0 is GREEDY (`decoding_overrides.greedy_first`: the fragment's
  own temperature 0, request-identical to the lock's single-sample request except the `seed` field, which a temperature-0 request does
  not consume); samples 1-4 are drawn at temperature 0.7 (seeds `fragment_seed + seed_offset + index`, i.e. offsets 0..4, the ROLL form);
* the in-flight delivered answer: `saea-commit-plurality-support-v1` at `min_support 3`, similarity 0.8 (the ROLL form for five samples; intent: plurality, ties to the
  lowest sample index, i.e. the greedy sample; entities: same-type clusters kept at support >= 3; s = 2 and 3-of-5 are both evaluated offline);
* a POOL cell: `offline-sealed-pool`, expected effect 0.0 pp, `claims_benefit` false, stage-3 label `inference-time-verification-v1`
  (operators scoring, selection). The VER-1 rule is SELECTED in the READ row's offline read together with the existing c3 columns.

## Why it is a hand-written fragment on a registered program id

* Program: `phase-native-module-v1-c6` is already a registered member of the review-off module program family
  (`rails.controllers.MODULE_PROGRAM_FAMILY_IDS`); the loader's graph ceiling for the grouped form is 1 + 1 x 5 = 6. No new program id.
* The module compiler has no `samples` knob and the loader verifies a declared `consumption_module` block against its own compilation,
  so the fragment declares no block; `ver1a_derive_cells.py` compiles the parent's block (minus the Perception template columns) to the
  R5 composed arm's blocks and asserts that nothing else moved beyond the registered diff.
* `native_episode.deliver_normaliser` is refused beside a grouped Solver visit (the delivered text is the commit policy's aggregate,
  re-derivable from the custodied samples). So v4g, lock v2.2's delivery rule, does NOT run in flight; it is applied OFFLINE to every
  custodied raw sample and to the replayed commit (`scripts/analysis/slurp_nx_postproc_v4_apply.py --apply v4g`), and the in-flight
  delivered score is the unprojected one (ROLL-2's precedent).

## Contact arithmetic

Per row: 1 Perception + 5 Solver = 6 (exact, no early exit). Arm: 1,080 x 6 = 6,480 generation calls; FIT 1,080 x 6 x 4 = 25,920
(structural); speech seconds `ceil(roster audio x 6)`. Smoke: 4 x 6 = 24 calls; FIT 96. GPU hours planned 2.5 (arm), 1.0 (smoke). The
generation budget is run-cumulative across attempts; the FIT cap never is.

## Identity-bound change (runtime)

`decoding_overrides.greedy_first` touches `rails/native_episode_config.py`, `reproduction/ojw/native_request.py` and
`reproduction/ojw/native_group_solver.py`; the prepared-artifact implementation identity binds the first (see the artifact-identity
lesson of 2026-09-19), so every earlier-pinned prepared artifact must be re-pinned after the merge. Absent the key every config behaves
byte for byte as before. Proof: `tests/unit/test_ver1a_greedy_first.py` (pure pieces, the four-row production walk (five samples: wire temperatures 0, 0.7 x 4, seeds 0..4), and the seal path
through `FlightRuntime._canonical_output_rows` plus the bundle outputs/trace binding).

## Order of operations (root)

countersign the four DRAFT flight rows (the READ row stays a draft until the seal) -> `scripts/flights/ver/ver1a_mint_receipt.py` ->
merge the engineering branch (no concurrent flip) -> `scripts/flights/ver/ver1a_flip.sh` -> `scripts/flights/refresh_registered_plan_pins.py`
-> flip again -> `scripts/flights/ver/ver1a_dry_run.py` (root: needs the data root) -> `scripts/flights/ver/ver1a_batch_chain.sh`.
`--allow-output-change` must never be passed. The first Fold B supply minted under this cell's run id is expected to equal the NX R1 / R6
digest; a different digest means the knowledge channel moved -- stop and report.

## Open items

* The READ row has a recipe (`analysis-recipe-v1.json`) but no wrapper script yet; one is added at countersign time, cloned from
  `scripts/flights/roll2/roll2_pool_read.sh`.
* Whether the greedy first sample reproduces the lock single-sample answer byte for byte is MEASURED in the read (stage 4), not assumed.
