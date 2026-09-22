# Preregistration -- cell B6, DEV-2000-ADDED direct-vs-plan paired read

Registered before contact on 2026-09-22 (owner decisions 34, 35, 78, 79, 86, 88), by script
(`scripts/flights/derive_slurp_b6_dev2000_cells.py`, decision 58).

## Question

On the fresh DEV-2000-ADDED roster (1,000 rows, split identity `ee6c43cd4dd8fc2a583d2dd053e799c2d002efa3755fcd092ba7c7565431bf67`, never before
flown for generation), how does the locked v2.0 default plan (cell B6 plan arm) compare with the bare
frozen core (cell B6 direct arm) in official pooled SLU micro F1, intent, scenario and action accuracy?
This is a **report-only fresh-roster generalisation read**, not a new admission decision: the plan was
already locked on TRAIN Fold A evidence (cell PLAN) and the direct form was already sealed on DEV-1000
and TRAIN Fold A.

## Arms

* **Direct** (`SAEA-SLURP-DIRECT-MAX512-DEV2000-ADDED-V1`): the sealed `slurp-direct-max512` form, unmodified, flown on
  DEV-2000-ADDED. Composed config hash `b8e38d6ac04d9e5fc793af83d6bba7c58647f3470e49eec04cf0b98bb17e1f59`, protocol hash `281b9f3bdaf38a4164fdb796a0ccfa1d32f3002ca495e1b4dc24069a82b45cd1`.
* **Plan** (`SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1`): the locked v2.0 default plan (cell PLAN's fragment), unmodified, flown on
  DEV-2000-ADDED. Composed config hash `b88f7b8285c9771a515ea378d6d8e53a5393694fedaae7fb6d9df8b4760d16bf`, protocol hash `e5e2ba6868f02a9b62ccfcd54ffe46a8e38f0bca5c4699f440bf95abbb40e93e`.

## Bindings

* Dataset fragment `slurp-speech-native-dev2000-added` (`configs/dataset/slurp-speech-native-dev2000-added.json`),
  roster receipt `docs/receipts/rosters/slurp-dev-2000-added-v1.json` (sha256 `f78dd8ad2894b1fd02bfe6050e39e3fb2c5d178a649e5d20e85ea4ecf4b8dc58`).
* Speech packet promotion receipt `/home/chao/feat-cache/slurp-q4km-packets-04ccc72a/DEV-2000-ADDED-promotion.json` (sha256 `978fc63888b99fa73ec5ca51ebb03676cb853f052125212f48326e213cf35091`).
* Intent-boundary query vectors `vectors/slurp-dev2000-added-v1/query-vectors-speech-segments.jsonl` (sha256 `e2a5fd046dac7c87fcf53830955e41e69d20402a2305a02ebf2bfc1a33001b9d`,
  1,000 rows, one segment each).
* Train-exemplars content-dimension query vectors `vectors/slurp-dev2000-added-v1/query-vectors-speech-content-v1.jsonl` (sha256
  `7d4ebdce553fd897fa86cc6b6d878ebf2298e19ee509eeceaf1aa0aca4855ee0`, 1,000 rows), built model-free by
  `scripts/build_slurp_query_content_derivative.py` from the intent-boundary file above (item 1 of this
  registration; tool-contact ledger row `SAEA-SLURP-DEV2000-ADDED-SPEECH-QUERY-ENCODING-V1`).
* Alias receipt `prepared/SAEA-SLURP-DEV2000-ADDED-ALIAS-V1/query-dimension-alias.json` (sha256 `9d41262d18b7dc524807e36fb1d97b859f43920524a6dfe85f1bead2b07a5768`), encoding receipt
  `preparation-runs/SAEA-SLURP-DEV2000-ADDED-SPEECH-QUERY-ENCODING-V1/encode-v1/receipt.json` (sha256 `9c2b6cdcb17ca3b1ad35b599217ca4e7d84f3c7e5a5d55056bdbf7d92fc9dc9d`), all `root: data`.

## No four-row smoke

Both forms are already sealed and flown: the direct max512 form on DEV-1000 and TRAIN Fold A, and the
locked plan on TRAIN Fold A (cell PLAN). Neither raises a new structural question a smoke would answer;
the only thing that moved is the roster-bound bindings enumerated above, and
`tests/unit/test_slurp_b6_dev2000_cells.py` proves those are the *only* things that moved, against both
precedents, byte for byte.

## No twin

Not registered; this cell reads two already-decided forms on a fresh roster, not a new mechanism.

## Metrics

Primary: official pooled SLU micro F1 (`slurp-slu-official`, devel gold scorer -- **not** the `-train`
sibling, since this is a `dev`-role roster). Secondaries: intent, scenario and action accuracy. Reported
beside: the per-scenario table in both the natural-mixture and the equal-scenario weighting (owner
decision 79 D3).

## Resampling

Paired bootstrap, 10,000 draws, seed 20260915, CI95, clustered on the **utterance id** (87 utterances
carry two recordings; owner decision 79 D2 clusters on the utterance, never on the individual recording,
so a paired draw never splits a twin-recording utterance across arms).

## Decision rule

**Report only.** No admission verdict is read from this cell: it reports the paired deltas (plan minus
direct) and their CI95, in both weightings, per owner decision 86 (development numbers carry no bar).

## What is not claimed

No admission or superiority verdict; no generalization or paper-scale claim (DEV-2000-ADDED is a
development roster, owner decision 28); no claim about other carriers; nothing about any in-flight cell.

## Resume-recovery clause

Copied unchanged from cell PLAN's own failure policy (owner decision 22 of 2026-09-18): if an attempt
dies of an INFRASTRUCTURE failure with code and request bytes unchanged -- never a harness or config
defect -- the one allowed recovery may be a RESUME-RECOVERY under item E10 instead of a re-fly: every
complete row of the aborted attempt is kept without selection, every partial or unstarted row is flown
under the same run id, and the merged manifest declares the predecessor attempt with its trace hash,
kept-row list and that list's hash. It changes no question, roster, factor, comparator, decision rule or
cap, and the run-cumulative budget must be re-checked because a resumed attempt and its predecessor share
one run id. A resumed EFFICIENCY read must additionally state the split of its GPU hours and prefilled
tokens across attempts.

## Readiness

Both cells `held`; decision readiness requirement carries a placeholder sha256 of 64 zeros pending the
coordinator's root admission decision and `scripts/flights/repin_cell.py` (see the package README).
