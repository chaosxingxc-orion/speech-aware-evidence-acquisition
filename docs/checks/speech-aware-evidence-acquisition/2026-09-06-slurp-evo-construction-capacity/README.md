# EVO-S1 construction capacity on SLURP TRAIN — there is no capacity wall

Model-free, zero contacts. Exposure row `SAEA-SLURP-MF-EVO-CONSTRUCTION-CAPACITY-V1`, registered
before the first count. Generator `scripts/build_slurp_evo_construction_capacity.py`; arithmetic
`src/speech_aware_evidence_acquisition/analysis/slurp_evo_capacity.py`; tests
`tests/unit/test_slurp_evo_construction_capacity.py`. Receipt `capacity.json`
(sha256 `a6251b207d7cdb0b5f4b5885cc4c5bbb3435c3534115a2af3e427dc145b800fc`).
Outbound connection attempts: **0**, enforced by `analysis.dev100_reviewer_audit.arm_offline_guard`
before the first byte is opened.

Authority: `docs/readiness/2026-09-05-three-dimension-experiment-program.md` sections 4c and 5,
transposed from tools to **scenarios**. `A_0` is the committed per-intent TRAIN slot schema
`docs/receipts/knowledge/slurp-intent-slot-schema-v1.json` (content hash `732e500a…7dcc`), which
this run **re-mined and reproduced exactly** before counting anything; a mismatch would have
refused the census.

## Verdict

**SLURP has no capacity wall, and the margin is not close.** The loop needs, per scenario, three
disjoint slices — 30 fold-A utterances, 30 fold-B utterances and an exemplar pool of at least 24
entity-bearing utterances — that is **84 utterances of which 24 carry entities**. The smallest
scenario in TRAIN is `cooking` with **211** utterances (+127 over the need) and the thinnest
exemplar pool is `audio` with **57** entity-bearing utterances (+33 over the quota). Every one of
the eighteen scenarios clears both tests, and sixteen of the eighteen clear the fold need by more
than 200 utterances.

This is the opposite finding to the Audio2Tool census of the same day, where nine of twenty-three
targeted tools could not supply two folds plus an eight-unit exemplar reserve and the loop's
arithmetic ceiling collapsed to +1.68 pp. The reason is structural rather than lucky: an Audio2Tool
target is a confusable *tool*, of which the corpus holds tens of rows, while a SLURP target is a
*scenario*, of which TRAIN holds hundreds. EVO-S1 is therefore the cell where the loop mechanism can
be tested without the corpus deciding the answer first.

## Population

TRAIN only, at source identity hash `545847bb95a9423005c71bdcc3fa74af55a3a1b6ae91409ba4070fd35bf92fef`
(the sha256 over the sorted `slurp:train:{id:06d}` utterance ids the schema receipt already binds).

| quantity | value |
|---|---:|
| utterances (the block unit) | 11,514 |
| real recordings | 50,628 |
| headset recordings | 24,210 (47.82 %) |
| far-field recordings | 26,418 (52.18 %) |
| distinct governed speakers | 166 |
| scenarios | 18 |
| intents (`scenario_action`) | 60 |
| utterances carrying at least one entity | 7,759 (67.4 %) |

**The block unit is the utterance id.** SLURP writes a sentence once and several speakers read it
into both a headset and a far-field microphone: 11,514 utterances become 50,628 recordings, 4.40 per
utterance. Every recording of a sentence must stay inside one fold, or a fold-B confirmation would
be re-scoring text fold A already selected on.

**No sentence text was read.** The `sentence` field is never consulted; `tokens[]` is joined only
inside `data.slurp`'s own entity-filler path, and only mention *counts* reach this receipt.

## Per scenario

`with entities` counts utterances carrying at least one gold entity — the exemplar pool. `types` is
the count of distinct gold entity types the scenario exhibits; `mentions` is the unfloored mention
mass (`load_slurp_intent_slot_schema(..., min_share=0.0)`), which is what `A_0`'s 2 %-floored table
is a projection of.

| scenario | TRAIN utterances | recordings | headset % | speakers | intents | entity mentions | types | with entities | zero-entity share | DEV-1000 rows | fold A | fold B | exemplars |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| alarm | 390 | 2,383 | 47.2 | 128 | 3 | 368 | 11 | 246 | 36.9 % | 58 | 30 | 30 | 24 |
| audio | 290 | 2,347 | 48.1 | 121 | 4 | 65 | 7 | **57** | **80.3 %** | 30 | 30 | 30 | 24 |
| calendar | 1,688 | 7,053 | 46.6 | 140 | 3 | 2,591 | 20 | 1,277 | 24.3 % | 61 | 30 | 30 | 24 |
| cooking | **211** | 824 | 47.6 | 111 | 2 | 201 | 9 | 170 | 19.4 % | 37 | 30 | 30 | 24 |
| datetime | 402 | 2,011 | 47.6 | 126 | 2 | 404 | 7 | 318 | 20.9 % | 61 | 30 | 30 | 24 |
| email | 953 | 3,852 | 47.2 | 135 | 4 | 842 | 17 | 632 | 33.7 % | 61 | 30 | 30 | 24 |
| general | 652 | 2,673 | 48.4 | 128 | 3 | 222 | 17 | 190 | 70.9 % | 61 | 30 | 30 | 24 |
| iot | 769 | 3,676 | 47.2 | 138 | 9 | 565 | 13 | 477 | 38.0 % | 61 | 30 | 30 | 24 |
| lists | 539 | 2,357 | 48.4 | 129 | 3 | 254 | 16 | 220 | 59.2 % | 60 | 30 | 30 | 24 |
| music | 332 | 1,458 | 47.1 | 129 | 4 | 117 | 13 | 94 | 71.7 % | 51 | 30 | 30 | 24 |
| news | 503 | 2,019 | 48.9 | 123 | 1 | 473 | 10 | 400 | 20.5 % | 60 | 30 | 30 | 24 |
| play | 1,377 | 6,600 | 48.7 | 138 | 5 | 1,294 | 25 | 1,030 | 25.2 % | 60 | 30 | 30 | 24 |
| qa | 1,183 | 4,351 | 49.2 | 132 | 5 | 968 | 13 | 811 | 31.4 % | 60 | 30 | 30 | 24 |
| recommendation | 433 | 1,635 | 47.5 | 123 | 3 | 456 | 14 | 307 | 29.1 % | 60 | 30 | 30 | 24 |
| social | 391 | 1,523 | 48.5 | 125 | 2 | 482 | 13 | 326 | 16.6 % | 60 | 30 | 30 | 24 |
| takeaway | 257 | 1,042 | 48.0 | 120 | 2 | 384 | 13 | 225 | 12.5 % | 39 | 30 | 30 | 24 |
| transport | 571 | 2,401 | 46.6 | 131 | 4 | 894 | 16 | 474 | 17.0 % | 60 | 30 | 30 | 24 |
| weather | 573 | 2,423 | 48.2 | 137 | 1 | 787 | 8 | 505 | 11.9 % | 60 | 30 | 30 | 24 |

Per-intent rows — all sixty, with the same columns plus the committed schema's kept-type count —
are in `capacity.json` under `intents`. The smallest intent by TRAIN utterances is the smallest
block the loop can ever be asked about; the schema block the loop evolves is keyed by intent, but
the *target* is the scenario, so a scenario's reward rows pool its intents.

## What the census says about the loop, beyond "it fits"

1. **The exemplar pool is the binding resource, not the fold pool.** Every scenario clears the fold
   need with at least +127 blocks, but `audio` (57), `music` (94) and `general` (190) are the three
   scenarios whose entity-bearing pool is thin enough that three seeded `M = 8` draws overlap
   heavily. They are also, in the KC-S1b per-stratum table, the three scenarios with the least
   headroom: `audio` moved +3.3, `music` **0.0** and `general` +4.4. The census and the verdict
   agree on which scenarios the loop has the least to work with.
2. **Zero-entity share predicts where a schema block can matter.** `weather` (11.9 % of TRAIN
   utterances carry no entity), `takeaway` (12.5 %), `social` (16.6 %) and `transport` (17.0 %) are
   the four densest scenarios, and they are exactly the four largest KC-S1b gains (+16.7, +1.7,
   +30.9, +13.6). `audio` at 80.3 % zero-entity and `music` at 71.7 % are the two the schema cannot
   say much about, and they are the two flattest strata.
3. **The recording mixture needs no correction.** TRAIN's natural mix is 47.82 % headset; DEV-1000's
   realized mix, drawn by the same one-recording-per-utterance rule, is 47.8 % (478 of 1,000). A
   fold drawn with that rule reproduces the evaluation surface's channel mixture without any quota,
   which is why the roster row prefers it to a forced 50/50.
4. **The DEV-1000 mixture the folds mirror is near-equal by construction.** The DEV ladder's
   capacity-aware apportionment gives 60 or 61 rows to thirteen scenarios and takes the other five
   whole (`audio` 30, `cooking` 37, `takeaway` 39, `music` 51, `alarm` 58). An equal 30-per-scenario
   fold is therefore the closest constant-quota approximation of the read population, and it is what
   the roster row freezes.

## What this row does not do

It freezes no roster (that is `SAEA-SN-MF-SLURP-EVO-FOLD-ROSTERS-V1`), authorizes no contact, opens
no devel or test file, and decides nothing about the loop's constants. It states the corpus's
capacity against the constants the program already fixed.
