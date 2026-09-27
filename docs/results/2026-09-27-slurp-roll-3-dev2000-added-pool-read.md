# Cell ROLL-3 read: the sealed five-sample pool on DEV-2000-ADDED -- per-sample intent 75.5 to 76.0, any-sample-correct 77.5, one intent across all five samples on 90.5 % of the rows with five parsed samples (DESCRIPTIVE)

Read 2026-09-27. The registered model-free read row `SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-READ-V1` (root
countersigned 2026-09-27 08:56:46 UTC at master `e2822b2b`, before any score was read) was executed by the
coordinator with the guarded wrapper `scripts/flights/roll3/roll3_pool_read.sh` (exit 0), which ran
`scripts/analysis/stage3_rollout_score.py` (stages render, score and pairs; the copy beside the output has
sha256 `8c5c2008e0a1c9790093018dc69b8a620e379cffeaf4c71bb990a19971801282`, the committed bytes at `e2822b2b`)
and `scripts/analysis/stage3_pool_spread_read.py` (stage 4 spread; copy sha256
`d6f97769c96aa6a854c5437e348536af6dcecc17e369835bcafdd684f9615382`, likewise), following the registered
recipe `slurp-stage3-roll-3-dev2000-added-sealed-pool-v1`
(`docs/readiness/2026-09-26-slurp-stage3-roll-3-dev2000-added-v1/analysis-recipe-v1.json`, sha256
`bbe076d40c204126ad479c71bf15f02f246816dbd780c7540a4d03ff299360aa`) stage by stage. This note was written by
Claude Opus 5.5 (worktree `/home/chao/saea-worktrees/fable-roll3rec`, branch `fable/roll3rec`) from the sealed
files only: nothing was re-run and no scorer was re-invoked. Analysis root
`$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-READ-V1` (machine results `spread.json`
sha256 `0d6261b55ccdc0f14e40287a0df129b2c6cf3932f0319f6b29aa96ca4772bd1b`, `ceiling.json`
`a137f68259cdeb67f09f1d84b626b82df72e0bdfec9f0145e6d0802f9650c14f`, `score-summary.json`
`34dd50f09e49a3b219fd5594307b211b041cccbc6bc8d9c05402323e6b222e6e`; every other file is hashed in
section 10). Contacts of the read: five CPU scorer jobs over derived copies (stage 2, the only contacts the
row registers) and zero model, tokenizer, encoder, embedder, llama-server, GPU and network contacts; nothing
under the sealed run directory was opened for writing. No utterance text, transcript, gold label string,
intent name, entity value or delivered answer is printed or persisted here or in the machine results.

Status: **DESCRIPTIVE** (an asset read: the per-sample scores, the within-flight sample spread, the oracle
ceiling as an upper bound and the sealed delivered score beside them, on the evaluation roster
DEV-2000-ADDED; no comparator, no gate, no admission, no effectiveness, superiority or generalisation claim,
and no disposition -- owner decisions 28 and 139; every number here is a development number).

## 1. What flew

Cell ROLL-2's grouped-Solver form, itself cell ROLL-1's, re-pointed onto DEV-2000-ADDED and changed in
nothing else: `native_episode.roles.solver` samples 5 at temperature 0.7 with the seeds 1249110493 to
1249110497, the commit `saea-commit-plurality-support-v1` at min_support 3 / similarity 0.8, the policy
program `phase-native-candidates-review-revise-samples5-v1` at a ceiling of 19 contacts per row, and no
deliver_normaliser node (a grouped Solver forbids one). Run `SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-V1`,
attempt `attempt-slurp-native-stage3-roll-3-dev2000-added-v1-generation`, flight commit `bc507604`
(`bc507604e2758e17a2e706f3e507fa3d1ec8ea16`) with an empty `study_repo_dirt`; attempt FINALIZED, manifest
COMPLETED (created 2026-09-27 08:15:52 UTC), 1,000 of 1,000 rows admitted. Contact window 2026-09-27
06:01:46 to 08:15:46 UTC on the resident session `serving-slurp-native-candidate-five-train-a-np4-v1`
(attached and reused, np4 x 24,576 = 98,304 tokens, max_tokens 512, model fragment
`q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1`; session receipt sha256
`19a9cee97097807b529b1ff764ca731575d78a356f33f8de71eeb51cf0eaefd1`), after the four-row form smoke
`SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-SMOKE-4-V1` sealed at 05:56:44 UTC. Decision receipt
`coordination/slurp-stage3-roll-3-dev2000-added-v1/root-admission-v1.json` under `SPEECHRL_DATA_DIR` (decision
id `slurp-stage3-roll-3-dev2000-added-admission-v1`, recorded 2026-09-27 05:04:42 UTC, sha256
`e4cd0f4f321e17e6ee45abf0c03962314fc46d2731ce9b5de1454a9b8802fd27`, eligible run ids the arm, the smoke and
their two FIT identities).

Roster: `SLURP-DEV-2000-ADDED-V1` (`docs/receipts/rosters/slurp-dev-2000-added-v1.json`, sha256
`f78dd8ad2894b1fd02bfe6050e39e3fb2c5d178a649e5d20e85ea4ecf4b8dc58`, split identity
`ee6c43cd4dd8fc2a583d2dd053e799c2d002efa3755fcd092ba7c7565431bf67`, split role dev, evaluation roster):
1,000 devel recordings of 913 utterances (87 utterances carry two recordings), 460 headset and 540 far-field,
2,983.527 s of speech; the receipt withholds the scenario stratum per item by design.

| artefact | sha256 |
| --- | --- |
| composed config / protocol hash | `c1d46e45fa74ee4a92cec4a9fb91506d19baf0b77ecebbc50fa1aa6d12549414` / `aff61447c94cfe38247fa0944fc0c10e7498aef5f0618490e56b63233f9504c0` |
| run manifest (as finalized on disk) | `f4ccc3f3df92749dc555817b187d27627fe9e41010fae1654e4ffc893c6ea774` |
| generation manifest (the pre-finalize seal) | `42586978bbbb4280244c820238cd9cfb166a3029aba50227fe2ad7d60183596d` |
| outputs | `7968e3cb236b992a5b49d81db013b1e6f085d1d7713447335e4d3333f05c1bf2` |
| scores (sealed, scorer id `slurp-slu-official`) | `b6b8946558c0b4c324f01f4861fab134234141ea9f9f87a903d78b6fac7f63c9` |
| phase artefact | `92a20ddd590b340e376157bce453570f194b7530b441f12b62e1b6da5e411a8c` |
| trace manifest / raw trace | `ec523700ddc129ecffbd32ce716443b49c2a5535bf4a326685b6c34a9635c72e` / `457369ea4f02142942a320495fa69a7fdb4d7c64d4f44937c72b848a9500ca4e` |
| flight receipts (file; its own `receipts_hash`) | `b5d23f2eb5c6eb95e5814048a64b433ca782fde2563d087d8b4d6a13108e0e7a` (`deff8e4d580bbba3662e71a348af1777fa1bc9f55a5f5f0390325db437e1584f`) |
| session-attach receipt | `49d81259ad786ef5c53ef39fdc97ce71751433958514f201651d980e00e52c48` |
| official score-batch result (one job, `succeeded`, 33.3 s, never sharded) | `6b0b8417997e3894b8224abbfacebc25a6cf594dcb59ed936f59ea422b00767b` |
| prepared first-phase supply (this run id's own) | `77284f0687290c6fbc79d2cb876e80436e5f314f1750a7ab77650d550ba49b46` |
| speech packet manifest (1,000 packets, 8 workers, 23.6 s) | `eb7b3c1e8028ff8b4e2a6cc9cf28e29b360692f51eb462033f7d7aca49241db0` |

Two manifest hashes, one file: the read's gold-free `accounting.json` (stage 1) lists under
`sealed_sha256.run_manifest` the value `42586978...`, the run manifest's hash at the seal (the flight
receipts' `seal.manifest_sha256`, equal to the generation manifest); the deferred finalize then rewrote the
run manifest to `f4ccc3f3...`, which the same file records as `score_stage.finalized_manifest_sha256`. Cite
`f4ccc3f3...` for the file on disk.

## 2. The recipe's gates

| stage | the recipe's requirement | result |
| --- | --- | --- |
| row accounting | 1,000 in, 1,000 out; every row's `solver_group` carries exactly 5 custodied samples with the five registered seeds and temperature 0.7 on each; the replay of `saea-commit-plurality-support-v1` at min_support 3 / similarity 0.8 reproduces the sealed delivered answer on every row; zero native task-contract calls | **held on every clause**: ids equal the roster (1,000 distinct); 1,000 rows with samples 0..4, the registered seeds on 1,000 and temperature 0.7 on all five samples of 1,000; the plurality replay equals the sealed delivered text on 1,000 of 1,000 rows and its sha256 equals the sealed `response_text_sha256` on 1,000 of 1,000 (intent support equal on 1,000, 0 replay failures); 0 native tool calls, 8,216 of 8,216 contacts answered as text; 17 malformed samples over 10 rows (4,983 of 5,000 samples parsed) |
| 1 render | one outputs copy per sample index, each row's `solver_group.samples[index].parsed_answer` rendered through the canonical path | the as-registered driver (the flight commit's `stage3_rollout_score.py`, sha256 `79371c36b3cde0d6f0af5d16cb6b007cdedab8a014c416376def9e37667fa9da`) REFUSED the roster (below); with the minimal fix of commit `243705e5` the five copies rendered, 1,000 rows each (section 10) |
| registration guard | stage 4 "REGISTERED SEPARATELY ... before any number is read" | the first execution stopped after render because the READ row was absent from the exposure ledger (commit `243705e5`); the row was countersigned at 08:56:46 UTC (`e2822b2b`); every score file of this read is timed 08:57:27 UTC or later |
| 2 score | each copy scored ONCE through `slurp-slu-official-projected-v3` against DEVEL gold; never `core.scoring_batch` | held: five complete jobs, 15.0 to 16.6 s each, at most four workers, identity check passed on all five; the micro SLU-F1 recomputed from each copy's official count fields reproduces its official aggregate to at most 1.2e-16 |
| 3 pairs | per-row best / worst and the sealed delivered score | per-row best / worst held; the sealed-delivered join is EMPTY by scorer id (below); 276 rows on which the five samples' per-row SLU-F1 differ |
| 4 spread | all ten sample-index pairs with CI95 by bootstrap over the utterance id (10,000 draws, seed 20260915), the byte-identical / intent-flip / entity-set-flip shares, the headset / far-field table, the ceiling as an upper bound, the delivered score beside | held: whole-cluster paired bootstrap over 913 utterance clusters (`analysis.paired.resampled_statistic`); sections 4 to 7 |

**The two places the seal contradicted the recipe, and what the driver did.** Quoted from commit
`243705e5`'s message:

> - scripts/analysis/stage3_rollout_score.py refused the registered roster as written ("roster item ...
>   carries no stratum"): the DEV-2000-ADDED receipt withholds the stratum per item by design. The minimal
>   change: when a roster declares stratum_withheld_per_item, group by the recording channel it does carry
>   (headset / far-field), which is the per-channel table the recipe asks for; any other stratum-free
>   roster is still refused. The as-registered refusal log and the unmodified driver bytes are pinned
>   beside the output.
> - The flight sealed the delivered answer under slurp-slu-official while the recipe scores the five copies
>   under slurp-slu-official-projected-v3, so the driver's sealed-delivered join is empty by scorer id;
>   the stage-4 driver reads the sealed delivered score under its own sealed scorer id and reports it
>   beside, never subtracted (a like-for-like projected delivered number would be a sixth scorer contact).

The as-registered refusal (`stage-render.as-registered.log`) ends
`Stage3ScoreError: roster item 'slurp:devel:000017:audio-1501773854-headset' carries no stratum`; the stage-3
log records the empty join as "no sealed delivered score for 'slurp-slu-official-projected-v3' ... known:
['cost', 'slurp-slu-official']". The sealed number is unprojected because a grouped Solver carries no
deliver_normaliser; the five copies are rendered through the canonical path and scored projected. The two
are therefore different scorer ids and are never differenced in this note.

## 3. The five samples

Official scores of each sample-index copy under `slurp-slu-official-projected-v3` (DEVEL gold, 1,000 rows,
one complete job each):

| sample index (seed) | intent | scenario | action | SLU-F1 | span F1 | score file sha256 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 0 (1249110493) | 75.5 | 81.1 | 77.7 | 63.53 | 54.68 | `d5cdac57c7aa9751a6a06fee7bdd3a2ec3d5e76adf7a9baf8bf2d8dbf2e78683` |
| 1 (1249110494) | 76.0 | 81.3 | 78.2 | 62.32 | 53.23 | `09540d48d3f4967e27ee5a516235ea9cc1678696d3dc8320f2e54e5c948c0871` |
| 2 (1249110495) | 75.7 | 81.1 | 78.0 | 63.73 | 54.93 | `fb4240033f8adf0a6a9db03b39d4570c60d4b8e34607acb787e76d37083aa2aa` |
| 3 (1249110496) | 75.9 | 81.1 | 78.1 | 64.01 | 55.21 | `4b21918432f723df3132fc11456810b434b5cd22e18b73575e3cf8cffc8d9bd5` |
| 4 (1249110497) | 75.7 | 81.2 | 77.9 | 61.94 | 53.02 | `195e8d30c29da3079f92576407abb13391a5378527f181c9127e2145c5626f27` |
| mean of the five | **75.76** | | | **63.11** | | |

Reported BESIDE, never subtracted (a different scorer id): the delivered plurality-commit answer as the
flight SEALED it at finalize under the unprojected `slurp-slu-official` -- intent 70.8, scenario 78.3,
action 73.4, SLU-F1 63.43, span F1 51.97 (sealed scores sha256
`b6b8946558c0b4c324f01f4861fab134234141ea9f9f87a903d78b6fac7f63c9`). For the record only: the delivered
bytes equal one sample's canonical rendering on 897 rows (103 rows are composites of the commit); on those
897 rows the attributed sample's projected intent is 75.92 and its micro SLU-F1 65.39 -- a SUBSET, never the
pool's delivered score.

## 4. The ceiling, stated as an upper bound

The oracle best-of-5 picks per row, AFTER seeing the gold, the sample with the highest official SLU-F1 (ties
by intent, then the lowest index). No selection policy can exceed it and none is claimed to reach it.

| quantity | intent | SLU-F1 (micro, official) |
| --- | ---: | ---: |
| oracle best-of-5 (UPPER BOUND): intent = some sample correct | **77.5** | **71.06** |
| mean of the five samples | 75.76 | 63.11 |
| oracle minus the mean sample | **+1.74** | +7.95 |
| worst-of-5 (intent = every sample correct) | 73.7 | 55.61 |

Oracle against each sample, micro SLU-F1 with CI95 (paired whole-cluster bootstrap, 10,000 draws, seed
20260915): +7.53 [+6.26, +8.87], +8.74 [+7.23, +10.32], +7.33 [+6.01, +8.69], +7.04 [+5.60, +8.57],
+9.12 [+7.68, +10.59] for samples 0 to 4. The oracle's chosen index is 0 on 837 rows, 1 on 59, 2 on 28, 3 on
60 and 4 on 16 (the tie-break sends identical rows to index 0). The per-row mean of SLU-F1 at the oracle is
52.04. Intent is joint scenario+action exact, and the SLU-F1 gap of 7.95 points
is carried by entity content: SLU-F1 scores entities, not intent.

## 5. The spread

| quantity | value |
| --- | ---: |
| rows whose five samples are byte-identical | 401 of 1,000 (40.1 %) |
| rows whose five samples carry one intent | **896 of 990 (90.5 %)**; 10 rows unknown (a malformed sample) |
| rows whose five samples carry one entity set | 496 of 990 (50.1 %) |
| rows whose five samples score one per-row SLU-F1 | 724 of 1,000 |
| pairwise mean over the ten index pairs: byte-identical | 61.46 % |
| pairwise mean: intent flip | 5.17 % (514 of 9,943 pair-rows) |
| pairwise mean: entity-set flip | 31.41 % |
| mean per-row absolute pairwise SLU-F1 difference / mean per-row sd across samples | 6.12 / 5.33 pp |

The ten pairs (B - A for pair A-B; CI95 by whole-utterance cluster bootstrap, 10,000 draws, seed 20260915;
flip denominators exclude rows where either sample is malformed):

| pair | byte-identical | intent flip | entity-set flip | delta per-row SLU-F1 | delta intent | delta micro SLU-F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0-1 | 620 / 1,000 | 52 / 994 | 302 / 994 | -0.41 [-1.54, +0.73] | +0.50 [-0.20, +1.21] | -1.21 [-2.71, +0.24] |
| 0-2 | 688 / 1,000 | 41 / 994 | 246 / 994 | +0.28 [-0.66, +1.24] | +0.20 [-0.50, +0.90] | +0.20 [-1.03, +1.42] |
| 0-3 | 609 / 1,000 | 48 / 995 | 324 / 995 | +0.29 [-1.00, +1.53] | +0.40 [-0.60, +1.40] | +0.49 [-1.30, +2.25] |
| 0-4 | 636 / 1,000 | 45 / 993 | 296 / 993 | -0.96 [-2.11, +0.22] | +0.20 [-0.51, +0.91] | -1.59 [-3.07, -0.10] |
| 1-2 | 709 / 1,000 | 35 / 995 | 243 / 995 | +0.70 [-0.36, +1.75] | -0.30 [-1.00, +0.30] | +1.41 [+0.13, +2.70] |
| 1-3 | 471 / 1,000 | 81 / 995 | 418 / 995 | +0.70 [-0.86, +2.25] | -0.10 [-1.19, +0.99] | +1.70 [-0.33, +3.75] |
| 1-4 | 692 / 1,000 | 43 / 994 | 257 / 994 | -0.55 [-1.53, +0.42] | -0.30 [-0.99, +0.39] | -0.38 [-1.78, +1.07] |
| 2-3 | 562 / 1,000 | 62 / 995 | 353 / 995 | +0.00 [-1.30, +1.31] | +0.20 [-0.70, +1.11] | +0.29 [-1.47, +2.01] |
| 2-4 | 665 / 1,000 | 36 / 993 | 279 / 993 | -1.24 [-2.27, -0.19] | +0.00 [-0.70, +0.70] | -1.79 [-3.10, -0.47] |
| 3-4 | 494 / 1,000 | 71 / 995 | 405 / 995 | -1.25 [-2.73, +0.23] | -0.20 [-1.21, +0.90] | -2.08 [-3.92, -0.23] |

Every pair compares two temperature-0.7 draws of one request that differ only by seed. Four of the ten
pooled micro SLU-F1 contrasts (0-4, 1-2, 2-4, 3-4) and one of the ten per-row SLU-F1 contrasts (2-4) have a
CI95 that excludes zero; none of the ten intent contrasts does. The ten pairs share samples, so they are
not ten independent tests. Reported beside as context: at temperature 0, two passes of one Solver visit
inside one np4 flight were byte-identical on 183 of 200 rows with 0 intent flips (ROLL-AA,
`docs/results/2026-09-24-slurp-stage3-roll-aa-within-flight-null-read.md`); a temperature-0.7 pool is a
different instrument and is not read against it.

## 6. The implied half-widths, beside the floors they are not

The within-pool paired instrument at n = 1,000: the CI95 half-width of a contrast between two sample indices
of this pool, over the ten pairs.

| contrast | mean | median | range over the ten pairs |
| --- | ---: | ---: | --- |
| per-row intent | **0.82** | 0.71 | 0.65 to 1.09 |
| per-row SLU-F1 | **1.19** | 1.15 | 0.95 to 1.55 |
| pooled micro official SLU-F1 | **1.56** | 1.48 | 1.23 to 2.04 |

CONTEXT, never a comparator and never a bar (owner decisions 28 and 139; the analysis root's
`reported-beside-context.json`, sha256 `c6351f5f94cdedf6c8b45585a796969353a72319e131ca80e40541f64b68254e`):
the offline sealed-pool floor of 0.67 pp at n = 625 (instrument note sections 2c and 2d, the aggregation
read over the ROLL-1 pool, which is the R01C construction roster although the context file labels it the
Fold A pool floor) and its scaling to about 0.51 pp at n = 1,080 (the ROLL-2 preregistration); the
DEV-2000-ADDED cross-flight own null, h_SLU 1.2525 and h_intent 1.1520 at n = 1,000 with a measured offset
of -0.25 pp (the B6 pair, PLAN vs PLANr); ROLL-AA's within-flight h 0.735 SLU / 0.000 intent at n = 200.
The ROLL-3 registration expected the pool to make actions readable offline at "about 0.53 pp at n =
1,000". The half-widths above measure a contrast between two independent temperature-0.7 draws of one pool;
the 0.67 of section 2c measured a delivery rule against its own pool (the medoid rule, +0.03 [-0.63,
+0.71]), on which most rows are identical by construction. They are different contrasts, and this note
re-estimates no floor.

## 7. Per channel

| quantity | headset | far-field |
| --- | ---: | ---: |
| rows / utterance clusters | 460 / 447 | 540 / 524 |
| per-sample intent, mean (range) | 80.13 (79.78 to 80.65) | 72.04 (71.48 to 72.59) |
| per-sample micro SLU-F1, mean (range) | 66.43 (64.78 to 67.15) | 60.12 (58.33 to 61.55) |
| oracle intent, some sample correct (UPPER BOUND) | 81.30 | 74.26 |
| oracle micro SLU-F1 (UPPER BOUND) | 74.49 | 67.96 |
| five samples byte-identical | 41.1 % | 39.3 % |
| pairwise mean: byte-identical / intent flip / entity-set flip | 62.4 % / 5.24 % / 30.1 % | 60.6 % / 5.09 % / 32.7 % |
| mean pairwise delta: SLU-F1 / intent (pp) | -0.52 / -0.26 | -0.01 / +0.33 |
| mean per-row absolute pairwise SLU-F1 difference | 6.79 pp | 5.54 pp |
| rows on which the samples' per-row SLU-F1 differ | 137 (29.8 %) | 139 (25.7 %) |

Headset recordings read higher than far-field ones in every sample, by 8.09 points of intent and 6.30 of
SLU-F1 on average over the five; the pairwise byte-identical and intent-flip shares of the two channels lie
within two points and 0.15 points of each other.

## 8. What this pool says about the route to 95

The programme's target is 95 per cent intent-recognition accuracy, absolute, measured on the test split
(owner decisions 137 and 141). On DEV-2000-ADDED the intent errors of the locked form are systematic across
samples: 896 of the 990 rows with five parsed samples (90.5 %) keep one intent across five temperature-0.7
samples, and the intent that some sample gets right is 77.5 against 75.76 for the mean sample (+1.74) and
73.7 for the all-samples-correct floor, so 38 rows (3.8 %) carry the gold intent in some but not all samples.
No rule that selects or aggregates among these five samples can deliver an intent above 77.5 on this roster,
17.5 points short of 95; sample selection or aggregation therefore cannot move intent materially here. This
is consistent with the closed aggregation line (owner decision 112: its offline read over the ROLL-1 pool
found no rule delivering one sampled response that separated from zero) and with the retrieval diagnosis
(`docs/results/2026-09-26-slurp-intent-retrieval-rank-diagnostic.md`: on this roster's sealed PLAN arm the
gold intent's boundary entry was outside the eight delivered on 149 of the 232 intent-wrong rows, spread down
the ranking tail, which that diagnosis reads as the binding constraint being knowledge the retrieval does not
deliver). This paragraph states what the numbers entail; it takes no verdict and no disposition (decisions
28 and 139).

## 9. Spend and dispositions

| quantity | ROLL-3 arm | four-row smoke |
| --- | ---: | ---: |
| generation contacts used / cap | **8,216 / 19,000** (8.216 per row: 961 rows at 8, 7 at 7, 31 at 15, 1 at 14) | 32 / 76 (8 per row) |
| speech audio seconds used / cap | 24,606.729 / 56,688 (roster 2,983.527 s, replayed 8.25x) | 65.022 / 155 |
| GPU, monitored active | **120.91 min (2.0152 GPU-h)** inside a 133.95 min monitor window; mean utilisation 75.5 %, parked fraction 0.097, mean 82.5 W, peak 97.9 W; cap 11.2 GPU-h fit-inclusive | 0.39 min (0.0065 GPU-h) inside 0.76 min; cap 1.0 |
| contact window (UTC, 2026-09-27) | 06:01:46 to 08:15:46 (134.00 min) | 05:55:48 to 05:56:44 |
| throughput over the contact window | 61.31 contacts per minute, 9,848.6 prompt tokens per second, slot occupancy 0.770, mean latency 3.02 s | -- |
| prompt / completion tokens | 79,185,386 / 344,207 | 250,720 / 1,540 |
| native tool calls | 0 (8,216 of 8,216 answered as text) | 0 (32 of 32) |
| dispositions | finite_completion 8 rows, planner_action_illegal 1 row, context compaction 0 contacts and 0 rows; Planner route records ACCEPT 989, REVISE 34 and one illegal action | all 0; Planner ACCEPT 4 |
| official scoring | one complete job at finalize, 33.3 s, never sharded | none (the smoke is scored by no one, by registration) |
| FIT identity | `SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-FIT-V1` opened no attempt state and no run directory; its 8,216 contact-fit receipts (contact class `tokenizer`, cache cold, 0 compactions) sit under `prepared/SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-FIT-V1/attempt-slurp-native-stage3-roll-3-dev2000-added-v1-fit/`, bound into the generation attempt's flight receipts; 8,216 of the 76,000 FIT endpoints | `SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-SMOKE-4-FIT-V1`, likewise: 32 receipts of 304 |

The registration expected about 8,550 contacts and about 3.3 GPU-h on the arm; realized 8,216 and 2.0152.
Beside, as context only: ROLL-2's sealed np4 arm ran at 63.07 contacts per minute and 9,515.8 prompt tokens
per second (`docs/results/2026-09-27-slurp-det-np1-pair-read.md`, section 4, over the arm's wall window as
the coordinator recorded it); the figure here uses this arm's sealed `run_phases` contact window.

The smoke (`attempt-slurp-native-stage3-roll-3-dev2000-added-smoke-4-v1-generation`, flight commit
`bc507604`, clean tree): manifest COMPLETED at 4 of 4 rows admitted (split identity
`fee83441e514473dc4ab798f8554882bc5753c7fc4924eda0e72c7af7ed51ef0`), five custodied samples per row with the
registered seeds and temperature 0.7 on 4 of 4, the plurality-support commit on 4 of 4; attempt state OPENED,
because the smoke registers no score and finalize is deferred to a score worker that the smoke never runs.
Run manifest (= generation manifest) sha256 `0946f2d76b86834993c6c5ca12cdbaaca29311c42f8a294d3b5e388e423a9779`,
outputs `6f7f4891f63b690782018f34bded8723e5a791f12b495d99deaae64c8d665c64`, phase artefact
`34f4c8d2c67319ae80ca94195b3ee9ebd2c4f54ca94aaf6c6f6ac35c16e524e0`, trace manifest
`6ed3cc45e87eae0150f58af514ee4003d8d8decacff0bcd97214dfcbcf12d126`, raw trace
`17e58fa1fd454ee2e235934230c1d25d2051a0fa6f863e7755d942285808e483`, flight receipts
`d70654f80a0f9a3449087cb640da3aa646d0318a96ed4855f57eec8e8ff2c4d4`. A form proof; no number is read from it.

## 10. Records

- `docs/exposure-ledger.md`: rows `SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-V1`,
  `SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-FIT-V1`, `SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-SMOKE-4-V1`,
  `SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-SMOKE-4-FIT-V1` and `SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-READ-V1`
  flipped to consumed with the sealed facts above and closed by a closure block each; no other row touched.
  The four flight rows' registration text still reads "draft, root countersignature pending" as registered;
  it is kept verbatim, and the decision receipt of section 1 is cited beside it.
- `docs/results/stage2-results-ledger.md` and `.json`: a DESCRIPTIVE entry for cell ROLL-3 (`SLURP-ROLL-3`,
  tally `instrument`).
- `docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md`: section 2e, the DEV-2000-ADDED pool's
  implied half-widths, pointing here.
- Analysis root, every file and its sha256: `accounting.json`
  `d271603c54b14ceb8265d37b96764cb8e854f09ced947cced4ea5dd1a0f5f8c0`, `render-manifest.json`
  `5f193003a43e3eae182a923b9bb208b2a74a9229ba6c392e383480a2dbd1e535`, `score-summary.json`
  `34dd50f09e49a3b219fd5594307b211b041cccbc6bc8d9c05402323e6b222e6e`, `pairs.json`
  `4f2112fa857ceb9be87d53361130af175d0ec7b0ec46b4dfa0db9743cc7dda79`, `per_row.json`
  `8ace6005fdfa1514a8377f53634fbbc18b40db56db4d825a671f4163807ed764`, `per_row_spread.json`
  `355e392150ab2a9855796516940fe51e94aa05a89cc492f8f2e98abc63cfd9ea`, `spread.json`
  `0d6261b55ccdc0f14e40287a0df129b2c6cf3932f0319f6b29aa96ca4772bd1b`, `ceiling.json`
  `a137f68259cdeb67f09f1d84b626b82df72e0bdfec9f0145e6d0802f9650c14f`, `reported-beside-context.json`
  `c6351f5f94cdedf6c8b45585a796969353a72319e131ca80e40541f64b68254e`; the five copies `sample-0-outputs.jsonl`
  to `sample-4-outputs.jsonl` `dad400e1f13bb225eb336a3a73eeef83ea2641be77e5c589f506c28d5f8e8890`,
  `187c326433228a9a79ee9a7a28f6ba4352cbc3eb72e06bbfed9b55d318f5af26`,
  `3fe1c6b58a9a310e1ac144d3bbbb7f5d22fb8d7d3958ccbded089819b63e6a85`,
  `d5a5f7634b6c3b3b7ff5696752dc19933aa005708883dcd3a2c16e049cc946d2`,
  `938eb266b184940450659f7212203fcb0fb5c167e9c9b95c5771170700d631b2`; their five score files as in
  section 3; the stage logs `stage-accounting.log` `4c7a2dd2b77a29203efb6524a83cf87b83bba257ca663e0e5233fef00230f370`,
  `stage-render.log` `fc09e66bdff487bf46741876f3097587214f9026542251ce494ce321b9b8db48`, `stage-score.log`
  `6b4364fb390f1c2127314d6e89e7532b88679a5d8eae0f26015bd56e2143e359`, `stage-pairs.log`
  `2e2f7dd045e1c756e1668af40a5c3384de71340fba52c95ec54be1572ed3fc02`, `stage-spread.log`
  `642d24cc6666ba320fed34950fb76b11204fbdb4cbe2dd02fda8c6fc60b2c34e`; the driver copies
  `stage3_rollout_score.py` `8c5c2008e0a1c9790093018dc69b8a620e379cffeaf4c71bb990a19971801282` and
  `stage3_pool_spread_read.py` `d6f97769c96aa6a854c5437e348536af6dcecc17e369835bcafdd684f9615382` (both equal
  to the committed bytes at `e2822b2b`); the as-registered driver `stage3_rollout_score.as-registered.py`
  `79371c36b3cde0d6f0af5d16cb6b007cdedab8a014c416376def9e37667fa9da` (equal to the flight commit `bc507604`'s
  bytes) and its refusal log `stage-render.as-registered.log`
  `758372d95bb9546a9b7980b79357e25f44d07e92b4e936b57fe009ae80cfb6f9`.
- Claim boundary: DESCRIPTIVE. The pool is an asset on a development roster; its numbers are neither a gain
  nor a loss of anything, and none of them may be read against another flight without an in-chain A/A
  replicate (the decision receipt's `not_authorized`). Development rows only (owner decisions 28 and 86).
