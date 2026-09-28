# Cell ROLL-2 read: the sealed five-sample pool on TRAIN Fold A -- per-sample intent 81.76 to 82.78, any-sample-correct 83.24, one intent across all five samples on 93.5 % of the rows with five parsed samples (DESCRIPTIVE)

Read 2026-09-28. The registered model-free read row `SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-READ-V1` (root
countersigned 2026-09-28 01:11 UTC by the coordinator, before any score was read) was executed with the
guarded wrapper `scripts/flights/roll2/roll2_pool_read.sh` (stage render 01:12:01Z, score 01:12:07Z, pairs
01:15:37Z, spread 01:16:22Z, done 01:18:46Z), which ran `scripts/analysis/stage3_rollout_score.py` (stages
render, score and pairs; the copy beside the output has sha256
`8c5c2008e0a1c9790093018dc69b8a620e379cffeaf4c71bb990a19971801282`, the committed bytes at `5f8b4c9d`, before
merge set A of the supply-variant instrument changed this driver) and `scripts/analysis/stage3_pool_spread_read.py`
(stage 4 spread; copy sha256 `d6f97769c96aa6a854c5437e348536af6dcecc17e369835bcafdd684f9615382`, equal to the
committed bytes), following the registered recipe `slurp-stage3-roll-2-fold-a-sealed-pool-v1`
(`docs/readiness/2026-09-26-slurp-stage3-roll-2-fold-a-v1/analysis-recipe-v1.json`, committed blob sha256
`d59cff5dcbd6469ae46c63335d8a47d8a17a61f5cfb10aa4cf5d1bfe48e15153`). This note was written by Claude Opus 5.5
(the merge and records agent, on master) from the sealed machine results only: nothing was re-run and no
scorer was re-invoked. Analysis root `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-READ-V1`
(`spread.json` sha256 `588b3986b75ed2f280825baac1aa34c27f8c463152671863077dfa36a0ca05f8`, `ceiling.json`
`88503eb52b396e21a91f3c71bcdd41463a1692bc6c278a4b043c770e936cf98f`, `per_row_spread.json`
`f06ba34ef338522512bd6ba553182679dd36cdcbf1054ffa350d6ab552322008`, `score-summary.json`
`4f00d3b43407730ee106fc5e9bbdd0f30e96b5cec509fd34d6ad62b8fe54e51b`, `render-manifest.json`
`7a891fe5fa867afc5234263ba7d2b9ed4d7f1cb602724dcf6f1973a8685eb504`). Contacts of the read: five CPU scorer
jobs over derived per-sample copies (stage 2, the only contacts the row registers) and zero model, tokenizer,
encoder, embedder, llama-server, GPU and network contacts. No utterance text, transcript, gold label string,
intent name, entity value or delivered answer is printed or persisted here or in the machine results.

Status: **DESCRIPTIVE** (an asset read: the per-sample scores, the within-flight sample spread, the oracle
ceiling as an upper bound and the sealed delivered score beside them, on the construction roster TRAIN
Fold A; no comparator, no gate, no admission, no effectiveness, superiority or generalisation claim, and no
disposition -- owner decisions 28 and 139; every number here is a development number).

## 1. What flew

Run `SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-V1`, attempt `attempt-slurp-native-stage3-roll-2-fold-a-v1-generation`,
manifest COMPLETED at flight commit `78bd241f` with a clean study tree (`study_repo_dirt` empty): the
grouped-Solver form (Solver samples 5 at temperature 0.7, seeds 1249110493..1249110497, the plurality-support
commit `saea-commit-plurality-support-v1` at min_support 3 / similarity 0.8, no deliver_normaliser) on the
1,080 rows of roster `SLURP-EVO-FOLD-A-V2` (split identity `61b0f062...`, role construction / discovery);
8,996 generation contacts of the 20,520 planned cap, 25,712.077 speech-audio seconds, 0 tool calls. Its
four-row smoke `SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-SMOKE-4-V1` sealed COMPLETED at the same commit with 32
contacts and 84.765 speech-audio seconds.

## 2. The recipe's custody clauses

| clause | result |
| --- | --- |
| row accounting | 1,080 in, 1,080 out; every row carries exactly 5 custodied samples with the registered seeds and temperature 0.7 |
| commit replay | the replay of `saea-commit-plurality-support-v1` reproduces the sealed delivered bytes on 1,080 of 1,080 rows (text and sha256); 0 replay failures |
| malformed samples | 7 samples over 3 rows (flip shares below exclude them as unknown) |
| micro recomputation | the stage-3 self-check recomputes each sample's official micro SLU-F1 to within 1.2e-16 |
| scorer-id mismatch (recorded) | the sealed run scored the delivered commit under `slurp-slu-official-train` (UNPROJECTED: a grouped Solver carries no deliver_normaliser), while the five copies are scored under the registered `slurp-slu-official-projected-v3-train`; the pairs stage logged that no sealed delivered score exists under the projected id. The two are reported side by side and never subtracted, as in ROLL-3 |

## 3. The five samples (projected scorer, official, pp)

| sample index (seed) | intent | scenario | action | SLU-F1 | span F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 (1249110493) | 82.31 | 88.33 | 83.52 | 62.38 | 51.82 |
| 1 (1249110494) | 81.76 | 87.59 | 83.15 | 61.71 | 51.25 |
| 2 (1249110495) | 81.94 | 87.69 | 83.24 | 62.06 | 51.67 |
| 3 (1249110496) | 82.78 | 88.15 | 83.98 | 63.26 | 52.77 |
| 4 (1249110497) | 82.04 | 88.06 | 83.43 | 60.24 | 49.13 |
| mean of the five | **82.167** | | | **61.93** | |

The delivered plurality commit, as the flight SEALED it under the unprojected `slurp-slu-official-train`
(scores sha256 `ca3bfe79...`): intent **80.185**, scenario 86.85, action 81.48, SLU-F1 **62.716**, span F1
50.65. A different scorer id from the rows above; beside, never subtracted. The delivered bytes equal one
sample's canonical rendering on **1,003 of 1,080 rows** (92.87 %; 77 rows composite); on that subset only the
attributed sample's projected intent is 81.95 and its micro SLU-F1 65.27 (the oracle on the same rows: 69.37)
-- a SUBSET, never the pool's delivered score.

## 4. The ceiling, stated as an upper bound

The oracle best-of-5 picks per row, AFTER seeing the gold, the sample with the highest official SLU-F1 (ties
by intent, then the lowest index). No selection policy can exceed it and none is claimed to reach it.

| quantity | intent | SLU-F1 (micro, official) |
| --- | ---: | ---: |
| oracle best-of-5 (UPPER BOUND): intent = some sample correct | **83.241** | **68.514** |
| mean of the five samples | 82.167 | 61.930 |
| oracle minus the mean sample | **+1.074** | **+6.584** |
| worst-of-5 (intent = every sample correct) | 81.204 | 55.090 |

Oracle against each sample, micro SLU-F1 with CI95 (paired whole-cluster bootstrap, 10,000 draws, seed
20260915; every Fold A row is its own utterance, so this is the paired row bootstrap): +6.13 [+4.96, +7.33],
+6.80 [+5.25, +8.37], +6.46 [+4.97, +7.96], +5.26 [+3.82, +6.70], +8.27 [+6.76, +9.84] for samples 0 to 4,
i.e. +5.26 to +8.27 with half-widths 1.18 to 1.56. The oracle's chosen index is 0 on 936 rows, 1 on 55, 2 on
19, 3 on 52 and 4 on 18 (the tie-break sends identical rows to index 0). The per-row mean SLU-F1 at the oracle
is 47.03. The SLU-F1 gap is carried by entity content; intent is joint scenario+action exact.

## 5. The spread

| quantity | value |
| --- | ---: |
| rows whose five samples are byte-identical | 488 of 1,080 (45.2 %) |
| rows whose five samples carry one intent | **1,007 of 1,077 (93.5 %)**; 3 rows unknown (a malformed sample) |
| rows whose five samples carry one entity set | 575 of 1,077 (53.4 %) |
| rows whose five samples score one per-row SLU-F1 | 825 of 1,080 (76.4 %) |
| pairwise mean over the ten index pairs: byte-identical | 64.55 % |
| pairwise mean: intent flip | 3.37 % |
| pairwise mean: entity-set flip | 29.49 % |
| mean per-row absolute pairwise SLU-F1 difference / mean per-row sd across samples | 5.26 / 4.57 pp |

Implied within-pool half-widths at n = 1,080 (the CI95 half-width of one sample-index pair's delta,
median over the ten pairs; context only, never a comparator or a bar): per-row intent 0.56, per-row SLU-F1
1.05, micro official SLU-F1 1.51. Reported beside them, also as context only: the Fold A offline pool floor
0.67 pp at n = 625 (0.51 scaled to 1,080), the Fold A cross-flight own null h_SLU 1.2485 / h_intent 0.9943,
and the ROLL-AA within-flight null h_within_SLU 0.735 at n = 200.

## 6. Per channel

| channel | rows | per-sample intent (s0..s4) | per-sample micro SLU-F1 (s0..s4) | oracle intent any | oracle micro SLU-F1 | all-5 byte-identical | pairwise intent flip | pairwise entity-set flip |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| headset | 523 | 82.79 / 82.03 / 82.41 / 83.56 / 82.22 | 63.06 / 63.72 / 63.74 / 62.50 / 61.96 | 83.75 | 68.60 | 47.4 % | 3.38 % | 27.1 % |
| far-field | 557 | 81.87 / 81.51 / 81.51 / 82.05 / 81.87 | 61.78 / 59.97 / 60.54 / 63.95 / 58.74 | 82.76 | 68.44 | 43.1 % | 3.34 % | 31.7 % |

Far-field rows carry the larger sample-to-sample SLU-F1 movement (mean per-row absolute pairwise difference
6.25 against 4.20 pp headset); the intent-flip share is the same on both channels.

## 7. Consequence for B3, the catch-all offline design

The B3 catch-all offline read (owner decision 171; package
`docs/readiness/2026-09-27-slurp-stage3-catchall-offline-v1/`) names this pool as its **primary** input: it
edits each of the five rendered per-sample copies of this read's stages 1-3 and scores each edited copy once
through the same registered scorer. At registration this read was absent; its per-sample copies and official
scores now exist, so B3's input precondition on Fold A is met (B3 itself still needs its own countersigned
row before any scoring). The numbers B3 fixed in advance are unchanged by this read: **20 marked Fold A rows**,
a reach ceiling (not a forecast) of 20 x 0.0926 = **1.85 pp** if every marked row were a gold catch-all and
every sample converted, and a floor of **0.5097 pp** at 1,080 rows. Beside them, this pool's own measured
within-pool per-row intent half-width is 0.56 (median pair), of the same order as B3's floor.

## 8. The mirror of the ROLL-3 finding: sampling cannot fix intent

On Fold A the intent errors of the locked form are systematic across samples, as on DEV-2000-ADDED
(ROLL-3, `docs/results/2026-09-27-slurp-roll-3-dev2000-added-pool-read.md` section 8): 1,007 of the 1,077
rows with five parsed samples (93.5 %; ROLL-3 90.5 %) keep one intent across five temperature-0.7 samples,
and the intent that some sample gets right is 83.24 against 82.17 for the mean sample (+1.07; ROLL-3 +1.74)
and 81.20 for the all-samples-correct floor, so about 22 rows (2.0 %) carry the gold intent in some but not
all samples. No rule that selects or aggregates among these five samples can deliver an intent above 83.24
on this roster, 11.76 points short of the programme's 95 per cent target (owner decisions 137 and 141,
measured on the test split); sample selection or aggregation therefore cannot move intent materially here.
The sampling headroom sits in SLU-F1 (oracle +6.58 over the mean sample), i.e. in entity content. This
paragraph states what the numbers entail; it takes no verdict and no disposition (decisions 28 and 139).

## 9. Records

- Exposure ledger: the READ row `SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-READ-V1` and the arm and smoke rows are
  closed by closure blocks citing this note; the two FIT identities are left as registered.
- Results ledger: one DESCRIPTIVE entry dated 2026-09-28.
- Machine results stay under the analysis root named above; nothing under `runs/` or the analysis root was
  opened for writing by this note.
