# Filler chunks c01 and c02 read: sealed five-sample pools on TRAIN Fold B -- per-sample intent 79.4 to 83.3, any-sample-correct 81.1 / 84.4, one intent across all five samples on 96.1 % / 94.4 % of the rows (DESCRIPTIVE)

Read 2026-09-29. The two registered model-free read rows `SAEA-SLURP-STAGE3-FILLER-FOLD-B-C01-READ-V1` and
`SAEA-SLURP-STAGE3-FILLER-FOLD-B-C02-READ-V1` (registered as drafts before launch at `1e472d54`; root
countersigned 2026-09-29T02:17:46Z by the coordinator, Fable 5.1, after both seals and before any number was
read; owner decisions 168 and 186) were executed with the guarded driver
`scripts/flights/filler/filler_pool_read.sh 1` and `... 2` (repo root = the read worktree `fable/fillerread`
at the countersignature commit). c01: render 02:18:10Z, score 02:18:11Z, pairs 02:21:31Z, spread 02:21:36Z,
done 02:21:55Z. c02: render 02:21:55Z, score 02:21:58Z, pairs 02:25:03Z, spread 02:25:07Z, done 02:25:26Z.
Driver copies beside the output: `stage3_rollout_score.py` sha256
`c12809878d4883d7ae333973779ce9f3efe0460eee90f9e2cb422753e1866ac2`, `stage3_pool_spread_read.py` sha256
`d6f97769c96aa6a854c5437e348536af6dcecc17e369835bcafdd684f9615382` (equal to the copy ROLL-2's read used).
Recipes `slurp-stage3-filler-fold-b-c01-sealed-pool-v1` and `...-c02-sealed-pool-v1`
(`docs/readiness/2026-09-27-slurp-stage3-filler-fold-b-cKK-v1/analysis-recipe-v1.json`).

Analysis roots:

- `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-FILLER-FOLD-B-C01-READ-V1` (`spread.json`
  `ed63fed001c31f3cb2186403b79cac0ef13b8f2bec711a8585f388a062ed4f91`, `ceiling.json`
  `9cc2af81400fc5608d40917c14ff2c8f5cf573a143398fca4cccf5d87a056c1b`, `per_row_spread.json`
  `9037fe463cef57e7b690c6fd5d711acc59d54ec34e13680bc407d77107b6fb12`, `score-summary.json`
  `b6363de1b24ab557c0a96fd72a55f22db3a8a0a80063a4710ba7ef81bdcf0538`, `render-manifest.json`
  `793e0eaf8582dc96f844c4b09288c804a157fd1d6ea77d617702f4324f29ff32`);
- `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-FILLER-FOLD-B-C02-READ-V1` (`spread.json`
  `2c92d008035ca851c76ee3bd71bccfaa4a2e804a90c14e6b0d1bb4bf694ca59a`, `ceiling.json`
  `8ec739a0c8f0ace27962e2da2349c488dc1c458ec838a697824a97c871e39efc`, `per_row_spread.json`
  `6bf60c431e61272d782e7179ab8e6039d087f6855e7a00695b00ffb073df8e0a`, `score-summary.json`
  `682a3d42248d82e1c0632fbd43263ec2cf5351b3e42820f907838c6d2c7b5ef9`, `render-manifest.json`
  `42e5a5a493a313556451d800104df4fdbf763202f5124e70c2580cdc0463652d`).

Contacts of the read: five CPU scorer jobs per chunk over derived per-sample copies (stage 2, the only
contacts the rows register) under the TRAIN-gold sibling `slurp-slu-official-projected-v3-train`; zero model,
tokenizer, encoder, embedder, llama-server, GPU and network contacts. No utterance text, transcript, gold label
string, intent name, entity value or delivered answer is printed or persisted here or in the machine results.

Status: **DESCRIPTIVE** (an asset read of two rollout pools of the sealed-credit inner loop's substrate: no
comparator, no gate, no admission, no effectiveness, superiority or generalisation claim, no disposition --
owner decisions 28, 139 and 162; TRAIN development numbers only, never a test claim; a 180-row chunk is
descriptive by size as well as by design).

## 1. What flew, and what the inner loop consumes

Runs `SAEA-SLURP-STAGE3-FILLER-FOLD-B-C01-V1` and `-C02-V1` (attempts
`attempt-slurp-native-stage3-filler-fold-b-cKK-generation-v1`), run and generation manifests COMPLETED at
study commit `1e472d54` with an empty `study_repo_dirt`: the current best SLURP system (locked PLAN plus the
agreement term, owner decision 161) in cell ROLL-2's grouped-Solver form (Solver samples 5 at temperature 0.7,
seeds 1249110493..1249110497, plurality-support commit at min_support 3 / similarity 0.8, no
deliver_normaliser) on the 180-row chunk rosters `SLURP-STAGE3-FILLER-FOLD-B-C01-V1` (split identity
`a7f41a89...`, 84 headset / 96 far-field) and `-C02-V1` (`236f5dc7...`, 92 headset / 88 far-field).

Per chunk the pool read produces: the five per-sample official scores under the `-train` projected sibling
(stage 2), per-row best / worst and the sealed delivered score (stage 3), and the within-pool spread, the
oracle best-of-5 / worst-of-5, the per-row sample agreement (all-five byte-identical, one intent, one entity
set, one per-row SLU-F1) and the implied within-pool half-widths (stage 4). What the sealed-credit inner loop
(`sealed-credit-system-policy-v1`, `core/stage3_algorithms.py`; status planned) consumes is the custodied
pool: the per-sample, per-row official scores (`per_row.json`, `per_row_spread.json`) with the custody fields
(expected seeds and temperature on every row, five samples per row, the commit replay reproducing the sealed
delivered bytes, the malformed-sample count). Credit and the update are computed over these sealed bytes; the
GPU is re-entered only for a composed policy.

## 2. Custody clauses

| clause | c01 | c02 |
| --- | --- | --- |
| row accounting | 180 in, 180 out; 5 custodied samples per row with the registered seeds and temperature 0.7 | same |
| commit replay | reproduces the sealed delivered bytes on 180 of 180 rows (text and sha256); 0 failures | same |
| malformed samples | 1 sample on 1 row | 2 samples on 1 row |
| micro recomputation | within 1.2e-16 of the official micro SLU-F1 | same |
| delivered bytes equal one sample's rendering | 170 of 180 (10 composite) | 163 of 180 (17 composite) |
| **entered the credit pool** | **180 rows, 900 samples (899 parsed; 179 rows with five parsed samples)** | **180 rows, 900 samples (898 parsed; 179 rows with five parsed samples)** |

The scorer-id split is as in ROLL-2 and ROLL-3: the flight sealed the delivered commit under the unprojected
`slurp-slu-official-train`, while the copies are scored under `slurp-slu-official-projected-v3-train`; the two
are reported side by side and never subtracted.

## 3. Per chunk (official, pp)

| quantity | c01 intent | c01 SLU-F1 | c02 intent | c02 SLU-F1 |
| --- | ---: | ---: | ---: | ---: |
| delivered plurality commit, SEALED (unprojected scorer; beside, never subtracted) | 79.444 | 66.013 | 81.111 | 63.464 |
| sample 0 (1249110493) | 80.00 | 64.78 | 82.78 | 63.18 |
| sample 1 (1249110494) | 81.11 | 63.90 | 83.33 | 63.20 |
| sample 2 (1249110495) | 81.11 | 66.78 | 82.78 | 62.50 |
| sample 3 (1249110496) | 79.44 | 67.84 | 82.22 | 60.42 |
| sample 4 (1249110497) | 81.11 | 66.04 | 83.33 | 62.53 |
| mean of the five samples | **80.556** | **65.867** | **82.889** | **62.365** |
| oracle best-of-5 (UPPER BOUND; intent = some sample correct) | **81.111** | **71.934** | **84.444** | **69.714** |
| oracle minus the mean sample | +0.556 | +6.067 | +1.556 | +7.349 |
| worst-of-5 (intent = every sample correct) | 79.444 | 59.531 | 81.111 | 55.181 |

Oracle against each sample, micro SLU-F1 (paired whole-cluster bootstrap, 10,000 draws, seed 20260915):
c01 +7.15 / +8.03 / +5.15 / +4.10 / +5.90 (CI95 half-widths 3.10 to 3.54); c02 +6.54 / +6.52 / +7.22 /
+9.30 / +7.18 (half-widths 2.76 to 3.86). Oracle chosen index (tie-break to 0): c01 156 / 7 / 5 / 9 / 3;
c02 156 / 12 / 2 / 7 / 3.

## 4. The spread and the per-row sample agreement

| quantity | c01 | c02 |
| --- | ---: | ---: |
| rows whose five samples carry one intent | **172 of 179 (96.1 %)**, 1 unknown | **169 of 179 (94.4 %)**, 1 unknown |
| rows whose five samples are byte-identical | 91 of 180 (50.6 %) | 79 of 180 (43.9 %) |
| rows whose five samples carry one entity set | 101 of 179 (56.4 %) | 92 of 179 (51.4 %) |
| rows whose five samples score one per-row SLU-F1 | 137 of 180 (76.1 %) | 134 of 180 (74.4 %) |
| pairwise mean: byte-identical / intent flip / entity-set flip | 70.44 % / 2.17 % / 25.24 % | 62.72 % / 2.84 % / 31.00 % |
| mean per-row absolute pairwise SLU-F1 difference / mean per-row sd | 4.55 / 4.09 pp | 4.87 / 4.30 pp |

Implied within-pool half-widths at n = 180 (the CI95 half-width of one sample-index pair's delta over the ten
pairs; context only, never a comparator or a bar):

| contrast | c01 median (mean; range) | c02 median (mean; range) |
| --- | --- | --- |
| per-row intent | 1.39 (1.08; 0.00 to 1.94) | 1.94 (1.78; 0.83 to 2.22) |
| per-row SLU-F1 | 2.07 (2.17; 1.56 to 2.95) | 2.36 (2.34; 1.91 to 2.81) |
| pooled micro official SLU-F1 | 3.32 (3.41; 2.46 to 4.36) | 3.36 (3.39; 2.40 to 4.35) |

Reported beside, context only: the offline pool floor 0.67 pp at n = 625 and the ROLL-AA within-flight null
h_within_SLU 0.735 / h_within_intent 0.0 at n = 200 (`reported-beside-context.json`).

Per channel (per-sample intent range; per-sample micro SLU-F1 range; oracle intent / oracle micro SLU-F1):
c01 headset 80.95-82.14; 69.95-75.79; 82.14 / 77.91 -- far-field 78.13-80.21; 59.28-62.33; 80.21 / 67.17.
c02 headset 82.61-84.78; 59.94-64.61; 84.78 / 70.20 -- far-field 80.68-82.95; 60.99-62.77; 84.09 / 69.13.

## 5. Beside ROLL-2 (Fold A) and ROLL-3 (DEV-2000-ADDED)

Same form (five samples, temperature 0.7, same seeds, plurality commit), but not the same system: ROLL-2 and
ROLL-3 flew the locked PLAN form, the filler chunks fly PLAN plus the agreement term; the rosters also differ
(TRAIN Fold A 1,080, DEVEL DEV-2000-ADDED 1,000, TRAIN Fold B 180 + 180). Beside, never subtracted.

| quantity | ROLL-2 Fold A | ROLL-3 DEV | filler c01 | filler c02 |
| --- | ---: | ---: | ---: | ---: |
| rows | 1,080 | 1,000 | 180 | 180 |
| mean-sample intent / SLU-F1 | 82.17 / 61.93 | 75.76 / 63.11 | 80.56 / 65.87 | 82.89 / 62.36 |
| oracle any-sample intent / best-of-5 SLU-F1 | 83.24 / 68.51 | 77.5 / 71.06 | 81.11 / 71.93 | 84.44 / 69.71 |
| oracle minus mean (intent / SLU-F1) | +1.07 / +6.58 | +1.74 / +7.95 | +0.56 / +6.07 | +1.56 / +7.35 |
| worst-of-5 intent / SLU-F1 | 81.20 / 55.09 | 73.7 / 55.61 | 79.44 / 59.53 | 81.11 / 55.18 |
| one intent across five samples | 93.5 % | 90.5 % | 96.1 % | 94.4 % |
| all five byte-identical | 45.2 % | 40.1 % | 50.6 % | 43.9 % |
| pairwise intent flip | 3.37 % | 5.17 % | 2.17 % | 2.84 % |
| pairwise entity-set flip | 29.49 % | 31.41 % | 25.24 % | 31.00 % |
| median half-width: per-row intent / per-row SLU / micro SLU | 0.56 / 1.05 / 1.51 | 0.71 / 1.15 / 1.48 | 1.39 / 2.07 / 3.32 | 1.94 / 2.36 / 3.36 |

The pattern of the two earlier pools holds on both chunks: intent is nearly fixed across samples (one intent
on 94-96 % of rows; oracle intent at most +1.56 over the mean sample), while the sampling headroom sits in
SLU-F1, i.e. entity content (oracle +6.1 to +7.3 over the mean sample). The chunk half-widths are about
sqrt(1,080 / 180) = 2.4 times ROLL-2's, as expected from n alone. This section states what the numbers entail;
it takes no verdict and no disposition (decisions 28 and 139).

## 6. Records

- Exposure ledger: the two READ rows countersigned (count 2); c03-c06 READ rows remain DRAFT. No closure
  block is added by this note.
- Results ledger: one DESCRIPTIVE entry dated 2026-09-29.
- Machine results stay under the two analysis roots; nothing under `runs/` was opened for writing.
