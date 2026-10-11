# VER-1 verification layer (owner decisions 257 / 258-A): Fold B pool read and Fold A confirmation read. The fixed rule is NOT CONFIRMED on Fold A (+0.56 [-0.40, +1.51] vs S0, +1.12 [-0.31, +2.56] vs the VER-1c lock column); the only form with CI-LB > 0 on every 5-sample pool is the support filter at n = 5, s = 2 (+0.76 .. +1.03 pp at 6 contacts per row)

Read 2026-10-11 by Claude Opus 5.5 (analysis agent, on the coordinator's brief, Fable 5.1) in the worktree
`opus/ver1-results` (base master `5005a393d`). Model-free: this note opened no model, server, encoder, embedder,
tokenizer or GPU, ran no scorer, and wrote nothing under the data root. It reads the aggregate outputs of the VER-1 offline
composer (`report.md`, `report.json` top-level fields) for the two VER-1 reads and the three earlier reads, the VER-1c
official per-arm column summary (`supply-variants/score-summary.json`, `render-manifest.json`), the readiness packages, the
decision registry and the ledger READ rows. No utterance text, transcript, gold value, slot filler, note body or model output
was printed or persisted. Only counts, rates, deltas, scenario labels, ids and hashes appear below.

**DESCRIPTIVE.** These are development numbers on TRAIN construction folds (owner decisions 28 and 86). Fold B is the
selection roster of the VER-1 rule. Fold A is the confirmation roster with the rule fixed before contact, but the c3 template
was authored from Fold A aggregate tables (VER-1c exposure disclosure). Nothing here is a test claim, a system-level claim or
an admission. Every pool cell claims no benefit. Where this note says NOT CONFIRMED it applies the criterion on file before the
Fold A flight. Decision 260 is the owner's.

## 0. Answer in eight lines

1. VER-1 as registered is **NOT CONFIRMED** on TRAIN Fold A. The fixed rule (n = 3, s = 2, c3 verdict x N1 >= 0.2, v4g) reads **+0.56 [-0.40, +1.51]** vs the pool's greedy sample S0 (66.41 %), +1.12 [-0.31, +2.56] vs the VER-1c lock column (65.85 %) and +0.87 [-0.48, +2.21] vs its twin. The criterion needs CI-LB > 0 and a point >= 0.67 pp.
2. On Fold B (the selection roster, VER-1a, 5 samples, S0 64.04 %) the same n = 3 form read +1.12 [+0.30, +1.94] (i1) / +1.19 [+0.36, +2.01] (i2) in-sample and +0.97 [+0.25, +1.70] / +1.10 [+0.33, +1.87] cross-fitted. The best in-sample combination was n = 5, s = 2 + gate: +1.29 [+0.54, +2.05] / +1.43 [+0.69, +2.16].
3. The Fold A components: filter alone +0.58 [-0.25, +1.40]; gate alone +0.49 [-0.05, +1.02]. Cross-fitting chose "no gate" on one half (+0.36 [-0.53, +1.25]).
4. The Fold A shortfall sits on non-empty-gold rows. Empty-gold contribution +1.37 [+0.93, +1.85]; non-empty **-0.87 [-1.72, -0.06]**; 36 false fills removed, 18 non-empty exact rows lost / 5 gained. On Fold B the non-empty side of the n = 3 rule was -0.14 / -0.20 (CIs span 0), and +0.04 at n = 5.
5. Intent is untouched. The `first-first` forms keep sample 0's labels and move 1 intent row against S0 on both folds.
6. Across folds the only form with CI-LB > 0 on every 5-sample pool read is the filter alone at n = 5, s = 2: VER-1a Fold B +0.85 [+0.35, +1.36], ROLL-2 Fold A +1.03 [+0.47, +1.70], ROLL-3 DEV +0.76 [+0.08, +1.45]. It costs 6 contacts per row against the lock's 2. The n = 3, s = 2 filter clears CI-LB > 0 on one of four pools (Fold B).
7. The c3 gate on a single column reads +0.49 .. +0.98 over five reads in three flight families. Its CI-LB is > 0 on three (R6 on the R1 i1 / i2 lock columns, VER-1a i2) and not on two (VER-1a i1, VER-1b Fold A).
8. The oracle ceilings stay large (Fold A: perfect gate on S0 +3.98, best of 3 samples +5.34; Fold B: best of 5 +8.77). Everything is DESCRIPTIVE on TRAIN folds (decision 28); nothing is admitted. Decision 260 is the owner's.

## 1. Inputs and identities

| item | VER-1a (Fold B pool) | VER-1b (Fold A pool) | VER-1c (Fold A c3 column) |
| --- | --- | --- | --- |
| run id | `SAEA-SLURP-STAGE3-VER1A-SAMPLES-FOLD-B-V1` | `SAEA-SLURP-STAGE3-VER1B-SAMPLES-FOLD-A-V1` | `SAEA-SLURP-STAGE3-VER1C-C3-COLUMN-FOLD-A-V1` |
| attempt | `attempt-slurp-native-stage3-ver1a-samples-fold-b-generation-v1` | `attempt-slurp-native-stage3-ver1b-samples-fold-a-generation-v1` | `attempt-slurp-native-stage3-ver1c-c3-column-fold-a-generation-v1` |
| package | `docs/readiness/2026-10-10-slurp-ver1a-samples-fold-b-v1/` | `docs/readiness/2026-10-10-slurp-ver1b-samples-fold-a-v1/` | `docs/readiness/2026-10-10-slurp-ver1c-c3-column-fold-a-v1/` |
| roster | `SLURP-EVO-FOLD-B-V2`, 1,080 rows (392 empty-gold); split identity `4407794c...` | `SLURP-EVO-FOLD-A-V2`, 1,080 rows (414 empty-gold); split identity `61b0f062...` | same as VER-1b |
| form | 1 Perception + 5 Solver per row; sample 0 greedy, samples 1-4 at T 0.7; in-flight commit plurality-support `min_support 3` | 1 Perception + 3 Solver; sample 0 greedy, samples 1-2 at T 0.7; commit `min_support 2` | E1 Solver template column: `r1-c3` (template sha256 `89b81e97...`, the R1 i1 bytes), `aa` twin, `lock` delivering |
| flight commit | `35ce8b9add7a859032bca09340c801a636563d3e` | `4088bb95c9ade0082cebd5a60daa0568fdad4369` | `e9629b3d485cc9d5cca1fab42e7a1f1514d344cb` |
| contacts | 6,480 (6 per row), 0 tool calls | 4,320 (4 per row), 0 tool calls | 4,320 (4 per row), 0 tool calls |
| seal | FINALIZED / COMPLETED; driver-done 2026-10-10T21:16:28Z; 109 min (~59 calls/min); smoke first try (24) | FINALIZED / COMPLETED; driver-done 2026-10-11T01:30:10Z; 103 min; smoke first try (16) | FINALIZED / COMPLETED; driver-done 2026-10-11T03:15:10Z; 100 min; smoke first try (16) |
| speech seconds | 18,928.8 | 12,338.1 | 12,338.1 |
| READ row | `SAEA-SLURP-STAGE3-VER1A-SAMPLES-FOLD-B-POOL-READ-V1`, countersigned 21:25:00Z (commit `b4cec7577`) | `SAEA-SLURP-STAGE3-VER1B-SAMPLES-FOLD-A-POOL-READ-V1`, countersigned 2026-10-11T01:40:00Z (`30077de25`) | `SAEA-SLURP-STAGE3-VER1C-C3-COLUMN-FOLD-A-COLUMN-READ-V1`, countersigned 03:25:00Z (`b2077f951`) |
| outputs sha256 | `18cb873918360e72c42b0db26bb3050db1052aa81417beae361a23026cd20059` | `611a76a1d389929de2fa14601e675e9be5911b60fdce8f12ff15a16a9ea59b2d` | `ad8b3329f6b647986f8f51c309c32043b894bbadcb67954a68e17e71f8fa735e` |
| run manifest | `0c54d5b0...` (ledger) | `25bd82b1...` (ledger) | `8e1257a390e78ab726aae0decca2b949a5feb92d5392f0eea19687b858125411` |
| sealed scores | `00543bc7aa9aabe6340f502cc88cd458f5e2be219219c4d51113073ac21846be` (in-flight commit, unprojected, 63.21 %; custody: 1,080 rows, 0 score mismatches) | `c0ad5639716930a63b0b1922321662a8bd992685c0b7cfdab7bb7bcfe5e21310` (63.99 %; 1,080 rows, 0 mismatches) | `cf227e8a97261f24b54c997af74b8edbb40bdcaa1f6502b95b15c32c69344139` |
| composer read | `analysis/SAEA-SLURP-VER1-OFFLINE-VER1A-FOLD-B/` (generated 2026-10-10T21:24:53Z) | `analysis/SAEA-SLURP-VER1-OFFLINE-VER1B-FOLD-A-V1/` (generated 2026-10-11T03:28:04Z), verdict source VER-1c `r1-c3` | official per-arm columns under the run's `supply-variants/` (3 scorer runs; at1 column reproduction checked on 1,080 rows) |
| composer sha256 (`driver_sha256`) | `2c9f20b018f9692be2a696ef46cc752817c4f164d24be94aceddc6c9b3c7b0ce` (= `scripts/analysis/slurp_ver1_offline.py` at `0bebc4804`) | `356355175fe81a7a2b170f2263ea4cb6df5f058ba809217bc32854a3ae59ff15` (= the file at `f81ef9a07`, unchanged at this note's base; adds `--verdict-run`) | - |
| report.json / report.md sha256 | `3679315c3022233a108766be0ee5332433fafa09f20fb62854d6177a3049d65b` / `8652899218d479ea4d74eed3dce887736cdd322b96b504e2470b4101d901f2eb` | `8f1d47778420ca26a6ed4a22e961a223e04497ad94e818d37fc8898a8726437d` / `f9ac7b891aa9df2644ea177f4af764faa0d6677998d1c3c8c241781ede718f71` | `score-summary.json` `7b149c8e3930ded1cb74e03cda8d7b61cb26c96f35de50beb296dc80ca59f458` |
| read grid | n {3, 5}; s {2, 3}; theta 0.1 .. 0.9; forms first-first, first-plurality, medoid-base; verdicts i1 (`r1-c3`, NX R1 i1) and i2 (`r1-i2-c3`, NX R1 i2) | restricted to the fixed rule: n 3, s 2, theta 0.2 (the default grids would be a Fold A re-selection) | - |
| N1 source | `phases.json` of `SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-V1` (sha256 `236cc47c...`); median fill 0 | `phases.json` of VER-1c (sha256 `d891e687...`); median fill 0 | - |
| bootstrap | whole-utterance clusters (1,080), 10,000 draws, seed 20260915 | same | - |
| read contacts | model, server, encoder, embedder, tokenizer, GPU, network, paid API, scorer subprocess: all 0 | all 0 | 3 official column scorings (READ recipe), 0 model |

Order of facts: the Fold A criterion was committed at `b7b248803` (2026-10-10T21:58:58Z) and the Fold A flight rows were
countersigned at `d3e29c843` (22:00:30Z), both before the first Fold A contact. Each composer read was generated after
its READ countersignature commit.

Earlier reads cited (all DESCRIPTIVE, all zero contacts; the ROLL-2 / ROLL-3 reads ran the composer at `0bebc4804`):
`analysis/SAEA-SLURP-VER1-OFFLINE-CONTROLS-V2/` (machinery controls), `...-ROLL2-FOLD-A-V2/` (ROLL-2 TRAIN Fold A pool, 5
samples at T 0.7, 1,080 rows, 414 empty-gold) and `...-ROLL3-DEV-V2/` (ROLL-3 DEV-2000-ADDED pool, 5 samples at T 0.7, 1,000
rows, 314 empty-gold, 913 utterance clusters). In the ROLL pools sample 0 is a T 0.7 draw, not a greedy decode.

## 2. Definitions

- **Support filter** `n<n>-s<s>-first-first`: sample 0's entities are kept iff at least `s` of the first `n` samples support
  them (same type, normalised-filler character F1 >= 0.8). Labels come from sample 0. A malformed sample 0 falls back to the
  lowest valid sample. On VER-1a, `n3` means samples 0-2 of the five.
- **Gate** `+gate[<source>,theta]`: empty the row where the c3 verdict column answered no entity after v4g AND N1 >= theta.
  N1 is the entity-free share of the 20 supplied exemplars. The gate moves no intent label.
- **The VER-1 rule fixed for Fold A** (VER-1b recipe, decision rule): n = 3, s = 2, base = sample 0 (greedy) with its own
  labels, gate = VER-1c `r1-c3` verdict x N1 >= 0.2, delivered through v4g. "NOT re-tuned on this roster".
- **The confirmation criterion, on file before the flight.**
  - VER-1b recipe, verbatim: "the rule is CONFIRMED iff its pooled SLU-F1 delta against the VER-1c lock column is at or
    above the 0.67 pp offline sealed-pool floor of the instrument note (section 2d) AND its CI95 lower bound is above zero
    AND the intent moves by no more than the 0.67 pp floor; anything else is reported as NOT CONFIRMED with the numbers,
    never softened."
  - Registry (decision 258 option A, criterion entry): "CONFIRMED iff the pooled official SLU-F1 delta of the rule over the
    VER-1c lock column (and over the pool's own greedy sample) has CI95 lower bound > 0 and a point >= 0.67 pp (the offline
    floor), with intent moved by at most 7 rows (decision 247 'stable')".
- **Comparators.**
  - `S0` is the pool's own sample 0 under the same normaliser. It is same-flight and paired row for row with every rule.
    In VER-1a / VER-1b it is the greedy decode.
  - `lock:<source>` and `aa:<source>` are the delivering lock column and its in-chain twin of the verdict flight. They are
    cross-flight against the pool: the R1 i1 / i2 flights on Fold B, VER-1c on Fold A.
    - In the Fold B report the R1 columns move with the normaliser (v3 62.13 / 63.43, v4g 63.69 / 64.86).
    - The VER-1c columns appear at the same value in both sections (lock 65.85, twin 66.11).
  - `DELIVERED` is the pool's in-flight commit re-scored in process: 3-of-5 on VER-1a, 2-of-3 on VER-1b.
  - `MEAN<n>` is the mean of the first n single-sample arms.
- **Primary.** The `## Normaliser v4g` section of each report is the lock base and the primary. The v3 section is context
  only and is not tabulated here (Fold B v3 deltas are larger: for example, n5-s2 + gate(i2) +2.51 vs S0).
- **Cross-fitting.** Utterance-hash halves. `s` (and `theta`, or "none") are chosen on one half and scored on the other. On
  Fold A the grid is the fixed rule only, so the cross-fit can only choose between gate and no gate.
- **Strata.** The empty / non-empty split is each gold half's contribution to the pooled delta, with the number of changed
  rows. Per-scenario deltas are within-scenario pooled (18 scenarios x 60 rows on both folds).
- **Exchange rates** (`docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md`, as carried in `report.json`): +0.033 pp
  per false-filled empty-gold row emptied, -0.070 pp per non-empty exact row lost, 0.056 pp per raw exact row (per 1,080
  rows). The `exch. pred.` column is that arithmetic, shown beside the realised delta.
- **Oracles** see the gold. They are upper bounds, never rules.

## 3. Fold B (VER-1a pool, 5 samples, v4g base)

Comparator levels (pooled official SLU-F1 % / intent %): S0 64.04 / 82.78; MEAN5 63.13 / 82.96; DELIVERED (3-of-5) 64.90
/ 83.33; lock:i1 63.69 / 82.22; aa:i1 64.22 / 82.41; lock:i2 64.86 / 83.15; aa:i2 64.41 / 82.96. Single samples 1-4:
63.76, 63.75, 62.92, 61.22.

### 3.1 Filter only (vs S0, and vs the R1 lock / twin columns)

| variant | SLU-F1 % | vs S0 | vs lock:i1 | vs aa:i1 | vs lock:i2 | vs aa:i2 | FF removed | NE lost / gained | intent rows | exch. pred. |
| --- | ---: | --- | --- | --- | --- | --- | ---: | --- | ---: | ---: |
| n3-s2 | 64.78 | +0.74 [+0.12, +1.36] | +1.10 [-0.15, +2.35] | +0.56 [-0.66, +1.80] | -0.08 [-1.39, +1.25] | +0.37 [-0.88, +1.65] | 11 | 4 / 5 | 1 | 0.433 |
| n3-s3 | 63.73 | -0.30 [-1.64, +0.93] | +0.05 [-1.46, +1.50] | -0.49 [-2.03, +0.96] | -1.13 [-2.79, +0.48] | -0.68 [-2.29, +0.88] | 32 | 22 / 11 | 1 | 0.286 |
| n5-s2 | 64.89 | **+0.85 [+0.35, +1.36]** | +1.20 [-0.02, +2.44] | +0.67 [-0.54, +1.88] | +0.03 [-1.25, +1.32] | +0.48 [-0.76, +1.72] | 9 | 2 / 5 | 1 | 0.507 |
| n5-s3 | 64.86 | +0.82 [-0.04, +1.67] | +1.17 [-0.07, +2.42] | +0.64 [-0.60, +1.89] | -0.00 [-1.33, +1.32] | +0.45 [-0.84, +1.75] | 23 | 11 / 7 | 1 | 0.479 |
| DELIVERED (n5-registered-s3) | 64.90 | +0.86 [-0.11, +1.85] | +1.21 [-0.01, +2.45] | +0.68 [-0.50, +1.89] | +0.04 [-1.24, +1.35] | +0.49 [-0.77, +1.75] | 16 | 14 / 15 | 6 | 0.598 |

### 3.2 Gate alone and filter + gate (theta 0.2)

| variant | SLU-F1 % | vs S0 | vs lock (same source) | vs aa (same source) | vs DELIVERED | FF removed | NE lost / gained | intent rows | exch. pred. |
| --- | ---: | --- | --- | --- | --- | ---: | --- | ---: | ---: |
| S0 + gate(i1) | 64.56 | +0.53 [-0.05, +1.08] | +0.88 [-0.32, +2.11] | +0.34 [-0.89, +1.64] | -0.34 [-1.36, +0.69] | 28 | 6 / 0 | 0 | 0.504 |
| S0 + gate(i2) | 64.86 | +0.82 [+0.25, +1.39] | -0.00 [-1.26, +1.28] | +0.45 [-0.77, +1.71] | -0.04 [-1.08, +1.02] | 35 | 7 / 0 | 0 | 0.665 |
| n3-s2 + gate(i1) (the rule later fixed) | 65.16 | +1.12 [+0.30, +1.94] | +1.47 [+0.23, +2.75] | +0.94 [-0.33, +2.25] | +0.26 [-0.68, +1.20] | 34 | 10 / 4 | 1 | 0.702 |
| n3-s2 + gate(i2) | 65.23 | +1.19 [+0.36, +2.01] | +0.37 [-0.95, +1.71] | +0.82 [-0.45, +2.11] | +0.33 [-0.64, +1.30] | 38 | 11 / 4 | 1 | 0.764 |
| n5-s2 + gate(i1) | 65.32 | **+1.29 [+0.54, +2.05]** | +1.64 [+0.41, +2.90] | +1.10 [-0.11, +2.37] | +0.43 [-0.53, +1.37] | 34 | 8 / 4 | 1 | 0.842 |
| n5-s2 + gate(i2) | 65.46 | **+1.43 [+0.69, +2.16]** | +0.60 [-0.67, +1.91] | +1.05 [-0.20, +2.33] | +0.56 [-0.42, +1.57] | 38 | 9 / 4 | 1 | 0.904 |

Under the Fold A criterion's form, the rule later fixed (n3-s2 + gate) would have passed against the R1 i1 lock column on
Fold B (+1.47 [+0.23, +2.75]) and failed against the R1 i2 lock column (+0.37 [-0.95, +1.71]). The two lock columns sit
1.18 pp apart on the same rows.

### 3.3 Cross-fitted (utterance-hash halves; vs S0, vs lock / twin of the same source)

| rule | chosen per half | vs S0 | vs lock | vs aa |
| --- | --- | --- | --- | --- |
| s, n3 | s2 / s2 | +0.74 [+0.12, +1.36] | - | - |
| s x theta, i1, n3 | s2 theta 0.3 / s2 theta 0.4 | +0.97 [+0.25, +1.70] | +1.32 [+0.09, +2.56] | +0.78 [-0.47, +2.05] |
| s x theta, i2, n3 | s2 theta 0.1 / s2 theta 0.4 | +1.10 [+0.33, +1.87] | +0.27 [-1.03, +1.63] | +0.72 [-0.55, +2.03] |
| s, n5 | s2 / s3 | +0.56 [-0.13, +1.25] | - | - |
| s x theta, i1, n5 | s2 theta 0.3 / s3 theta 0.6 | +0.78 [+0.02, +1.56] | +1.14 [-0.10, +2.39] | +0.60 [-0.64, +1.87] |
| s x theta, i2, n5 | s2 theta 0.1 / s3 theta 0.4 | +1.08 [+0.26, +1.90] | +0.26 [-1.10, +1.60] | +0.71 [-0.58, +2.03] |

### 3.4 Oracle ceilings (vs S0)

n3: best of 3 samples +4.32; perfect gate on S0 +3.22; perfect gate on filter s2 +3.60; perfect verdict gate on S0 +1.24
(i1) / +1.74 (i2); best of rules +2.59. n5: best of 5 samples **+8.77**; perfect gate on filter s2 +3.73; on filter s3 +3.31;
best of rules +2.31.

Verdict columns on Fold B: i1 answered no entity on 468 rows (334 empty-gold: precision 71.4 %, recall 85.2 % of 392);
i2 on 467 rows (346: 74.1 %, 88.3 %).

## 4. Fold A (VER-1b pool, 3 samples, v4g base; VER-1c comparators)

Comparator levels: S0 66.41 / 86.20; MEAN3 65.31 / 85.96; DELIVERED (2-of-3) 67.00 / 86.02; lock:r1-c3 65.85 / 86.11; aa:r1-c3
66.11 / 86.02. Single samples 1-2: 63.99, 65.53. The greedy sample S0 sits 0.56 pp above the VER-1c lock column and 0.31 pp
above its twin, all on the same 1,080 rows from different flights.

VER-1c official columns (`score-summary.json`, scorer `slurp-slu-official-train`, levels only):

| arm | SLU-F1 % | span-F1 % | intent % | entity precision / recall % |
| --- | ---: | ---: | ---: | --- |
| `lock` (delivering) | 65.85 | 56.14 | 86.11 | 57.75 / 54.62 |
| `aa` twin | 66.11 | 56.03 | 86.02 | 57.87 / 54.30 |
| `r1-c3` | 65.63 | 55.92 | 86.11 | 61.27 / 51.43 |

The `r1-c3` verdict answered no entity on 475 rows (351 empty-gold: precision 73.9 %, recall 84.8 % of 414). Malformed first
visits: `r1-c3` 1, `aa` 1, `lock` 0.

### 4.1 The fixed rule and its components

| variant | SLU-F1 % | intent % | vs S0 | vs lock:r1-c3 | vs aa:r1-c3 | vs DELIVERED | vs MEAN3 | FF removed | NE lost / gained | intent rows | exch. pred. |
| --- | ---: | ---: | --- | --- | --- | --- | --- | ---: | --- | ---: | ---: |
| filter n3-s2 | 66.99 | 86.30 | +0.58 [-0.25, +1.40] | +1.14 [-0.20, +2.52] | +0.88 [-0.43, +2.18] | -0.01 [-0.62, +0.59] | +1.68 [+0.84, +2.53] | 23 | 12 / 5 | 1 | 0.269 |
| gate S0 + gate(r1-c3, 0.2) | 66.91 | 86.20 | +0.49 [-0.05, +1.02] | +1.06 [-0.25, +2.38] | +0.80 [-0.45, +2.07] | -0.10 [-1.13, +0.94] | +1.59 [+0.62, +2.58] | 25 | 6 / 0 | 0 | 0.405 |
| **fixed rule: n3-s2 + gate(r1-c3, 0.2)** | 66.97 | 86.30 | **+0.56 [-0.40, +1.51]** | **+1.12 [-0.31, +2.56]** | +0.87 [-0.48, +2.21] | -0.03 [-0.80, +0.72] | +1.66 [+0.69, +2.65] | 36 | 18 / 5 | 1 | 0.278 |
| DELIVERED (n3-registered-s2) | 67.00 | 86.02 | +0.59 [-0.37, +1.54] | +1.15 [-0.21, +2.53] | +0.90 [-0.42, +2.23] | +0.00 | +1.69 [+0.97, +2.41] | 13 | 12 / 10 | 4 | 0.289 |

Context forms, same table, not the fixed rule:
- n3-s2 medoid-base + gate: +0.85 [-0.20, +1.91] vs S0, +1.42 [-0.01, +2.84] vs lock.
- n3-registered-s2 + gate: +0.78 [-0.27, +1.84] / +1.35 [-0.08, +2.78].
- The first-plurality variants move 4 intent rows.

### 4.2 Cross-fitted (gate or no gate, chosen per half)

| rule | chosen per half | vs S0 | vs lock:r1-c3 | vs aa:r1-c3 |
| --- | --- | --- | --- | --- |
| s, n3 first-first | s2 / s2 | +0.58 [-0.25, +1.40] | +1.14 [-0.20, +2.52] | +0.88 [-0.43, +2.18] |
| s x theta, r1-c3, n3 first-first | s2 none / s2 theta 0.2 | +0.36 [-0.53, +1.25] | +0.93 [-0.46, +2.32] | +0.67 [-0.64, +1.98] |

### 4.3 Oracle ceilings (vs S0)

Best of 3 samples **+5.34**; perfect gate on S0 **+3.98**; perfect gate on filter s2 +3.82; perfect verdict gate on S0
(r1-c3) +1.47; best of rules +1.73.

### 4.4 The criterion, applied

| test | value | met |
| --- | --- | --- |
| delta vs VER-1c lock column >= 0.67 pp | +1.12 | yes |
| CI95-LB vs VER-1c lock column > 0 | -0.31 | **no** |
| delta vs the pool's greedy sample >= 0.67 pp (registry form) | +0.56 | **no** |
| CI95-LB vs the greedy sample > 0 (registry form) | -0.40 | **no** |
| intent moved <= 0.67 pp (recipe) / <= 7 rows (registry) | +0.09 pp and 1 row vs S0; 86.30 vs 86.11 = +0.19 pp vs the lock column | yes |

Result: **NOT CONFIRMED** under both written forms of the criterion.

## 5. Strata and per-scenario (v4g, vs S0)

### 5.1 Empty / non-empty contribution to the pooled delta (changed rows)

| fold | variant | pooled | empty-gold | non-empty-gold |
| --- | --- | --- | --- | --- |
| B | n3-s2 | +0.74 | +0.47 [+0.22, +0.77] (13) | +0.25 [-0.33, +0.82] (40) |
| B | n5-s2 | +0.85 | +0.41 [+0.18, +0.69] (11) | +0.43 [+0.01, +0.86] (24) |
| B | n5-s3 | +0.82 | +0.86 [+0.52, +1.24] (24) | -0.08 [-0.85, +0.66] (63) |
| B | n3-s2 + gate(i1) | +1.12 | +1.21 [+0.83, +1.64] (36) | -0.14 [-0.85, +0.55] (54) |
| B | n3-s2 + gate(i2) | +1.19 | +1.34 [+0.93, +1.79] (40) | -0.20 [-0.91, +0.47] (53) |
| B | n5-s2 + gate(i1) | +1.29 | +1.21 [+0.83, +1.64] (36) | +0.04 [-0.58, +0.65] (41) |
| B | n5-s2 + gate(i2) | +1.43 | +1.34 [+0.93, +1.79] (40) | +0.04 [-0.56, +0.62] (39) |
| A | n3-s2 | +0.58 | +0.89 [+0.55, +1.28] (25) | -0.36 [-1.09, +0.37] (59) |
| A | **n3-s2 + gate(r1-c3)** | +0.56 | +1.37 [+0.93, +1.85] (38) | **-0.87 [-1.72, -0.06]** (71) |

The same rule changed 54 non-empty-gold rows on Fold B (i1) and 71 on Fold A. Its non-empty side went from -0.14 to -0.87,
while the empty-gold side was about the same (+1.21 vs +1.37).

### 5.2 Per-scenario delta (pp, within-scenario pooled; 60 rows each; CIs in `report.json`)

| scenario | B n3-s2 | B n5-s2 | B n3-s2+g(i1) | B n5-s2+g(i1) | B n3-s2+g(i2) | B n5-s2+g(i2) | A n3-s2 | A n3-s2+g(r1-c3) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | +0.92 | +0.92 | +0.92 | +0.92 | +0.92 | +0.92 | +1.60 | +1.60 |
| audio | +1.43 | +1.43 | +4.51 | +4.51 | +7.94 | +7.94 | +2.65 | +7.96 |
| calendar | -0.07 | -0.37 | -0.07 | -0.37 | -0.07 | -0.37 | +0.90 | +0.64 |
| cooking | +0.56 | +0.56 | +1.20 | +1.20 | +1.20 | +1.20 | +0.03 | +0.58 |
| datetime | +0.71 | +0.71 | -0.55 | -0.55 | -0.55 | -0.55 | -0.38 | -0.49 |
| email | +0.76 | +0.76 | +2.31 | +2.31 | +3.94 | +3.94 | -0.19 | +0.49 |
| general | +6.68 | +4.99 | +6.92 | +5.95 | +4.07 | +3.13 | +2.59 | -2.78 |
| iot | +1.14 | +0.54 | +2.39 | +2.39 | +2.39 | +2.39 | +0.23 | +2.05 |
| lists | +0.56 | -0.53 | -4.07 | -4.07 | -3.93 | -3.93 | +2.79 | -0.38 |
| music | +1.36 | +1.36 | +1.98 | +1.98 | +1.98 | +1.98 | +7.93 | +7.93 |
| news | -0.64 | +0.55 | +0.48 | +1.67 | -0.09 | +1.11 | -3.73 | -2.88 |
| play | -0.20 | +1.54 | +0.54 | +1.48 | +2.59 | +4.90 | +1.84 | +3.30 |
| qa | +0.00 | +0.00 | +3.19 | +3.19 | +2.53 | +2.53 | +0.57 | +1.96 |
| recommendation | +1.20 | +1.20 | +0.54 | +0.54 | +0.54 | +0.54 | +0.47 | -0.61 |
| social | +0.33 | +0.76 | +0.33 | +0.76 | -0.52 | -0.08 | +0.95 | -0.64 |
| takeaway | +0.84 | +0.46 | +0.84 | +0.46 | +0.84 | +0.46 | -0.52 | -0.52 |
| transport | -0.38 | +0.71 | -0.71 | +0.40 | -0.71 | +0.40 | +0.32 | -0.55 |
| weather | +0.73 | +1.23 | +0.73 | +1.23 | +0.73 | +1.23 | -2.02 | -2.02 |

The gate's per-scenario sign is not stable across folds. `general` is +6.92 on Fold B (i1) and -2.78 on Fold A; `lists`
is -4.07 on Fold B and -0.38 on Fold A (where the filter alone reads +2.79). `audio`, `iot`, `play` and `qa` gain from the
gate on both folds. Single scenarios of 60 rows are diagnostics.

## 6. Cross-pool view

### 6.1 The support filter over v4g, vs the pool's own sample 0 (`first-first`)

| pool | sample 0 | S0 % | n5-s2 | n5-s3 | n3-s2 | n3-s3 |
| --- | --- | ---: | --- | --- | --- | --- |
| VER-1a TRAIN Fold B (1,080) | greedy | 64.04 | **+0.85 [+0.35, +1.36]** (FF 9, NE 2 / 5) | +0.82 [-0.04, +1.67] | +0.74 [+0.12, +1.36] | -0.30 [-1.64, +0.93] |
| ROLL-2 TRAIN Fold A (1,080) | T 0.7 | 64.40 | **+1.03 [+0.47, +1.70]** (FF 13, NE 3 / 3) | +0.87 [-0.24, +2.04] | +0.91 [-0.07, +2.03] | +0.33 [-1.31, +1.99] |
| ROLL-3 DEV-2000-ADDED (1,000; 913 clusters) | T 0.7 | 64.63 | **+0.76 [+0.08, +1.45]** (FF 17, NE 3 / 3) | +0.22 [-0.70, +1.14] | +0.18 [-0.71, +1.06] | -1.62 [-2.97, -0.32] |
| VER-1b TRAIN Fold A (1,080) | greedy | 66.41 | not read (3 samples) | - | +0.58 [-0.25, +1.40] | - |

Facts from these tables:
- n5-s2 has CI-LB > 0 on all three 5-sample pools: +0.76 .. +1.03 pp, 0 intent rows on Fold A, 1 on Fold B, 4 on DEV.
- On all three, its non-empty side is flat: Fold B +0.43 [+0.01, +0.86], ROLL-2 +0.27 [-0.11, +0.66], ROLL-3 +0.18
  [-0.43, +0.82].
- n3-s2 clears CI-LB > 0 only on VER-1a. The ROLL-2 / ROLL-3 n3 forms lose on non-empty rows: -0.90 [-1.64, -0.20] and
  -0.97 [-1.78, -0.19].
- On ROLL-3 the n5-s2 equal-scenario figure is +1.10 [+0.50, +1.83] (natural +0.76); the folds have equal scenarios.
- Cross-fitted s at n = 5: VER-1a s2 / s3 +0.56 [-0.13, +1.25]; ROLL-2 s2 / s3 +0.56 [-0.28, +1.41]; ROLL-3 s2 / s2 +0.76
  [+0.08, +1.45].

### 6.2 The c3 verdict x N1 >= 0.2 gate on one column, across flights (v4g)

| read | column gated | delta | FF removed | NE exact lost | intent rows |
| --- | --- | --- | ---: | ---: | ---: |
| R6 offline / controls V2, R1 i1 | R1 i1 lock column | +0.75 [+0.27, +1.24] | 27 (91 -> 64) | 3 | 0 |
| R6 offline / controls V2, R1 i2 | R1 i2 lock column | +0.98 [+0.50, +1.48] | 33 (93 -> 60) | 3 | 0 |
| VER-1a, verdict i1 | VER-1a greedy S0 | +0.53 [-0.05, +1.08] | 28 | 6 | 0 |
| VER-1a, verdict i2 | VER-1a greedy S0 | +0.82 [+0.25, +1.39] | 35 | 7 | 0 |
| VER-1b, verdict VER-1c r1-c3 | VER-1b greedy S0 | +0.49 [-0.05, +1.02] | 25 | 6 | 0 |

On the R6 reads the verdict and the gated column come from the same flight. On VER-1a / VER-1b they come from different
flights over the same rows, and the gated column loses about twice as many non-empty exact rows (6-7 vs 3).

## 7. Cost (contacts per row; the lock v2.2 delivery is 1 Perception + 1 Solver = 2)

| form | contacts per row | Fold B vs S0 | Fold A vs S0 |
| --- | ---: | --- | --- |
| lock v2.2 (S0-equivalent single decode) | 2 | - | - |
| gate alone (+1 c3 verdict contact) | 3 | +0.53 / +0.82 | +0.49 |
| filter n = 3, s = 2 | 4 | +0.74 | +0.58 |
| filter n = 3, s = 2 + gate (the fixed rule; decision 258 arithmetic) | 5 | +1.12 / +1.19 | +0.56 |
| filter n = 5, s = 2 | 6 | +0.85 | not flown |
| filter n = 5, s = 2 + gate | 7 | +1.29 / +1.43 | not flown |

Flight wall time:
- VER-1a: 6,480 contacts in 109 min (about 59 per minute).
- VER-1b: 4,320 contacts in 103 min.
- VER-1c: 4,320 contacts in 100 min.

Planned GPU hours at registration were 2.5 / 1.7 / 1.8. The registry notes that the samples share the prefix cache, so wall
time grows less than the contact count. Against a delivery of 2 contacts, the n = 5, s = 2 filter costs 3x and the
fixed rule 2.5x.

## 8. What the verdict means and does not

| question | Fold B (selection) | Fold A (confirmation, rule fixed) |
| --- | --- | --- |
| fixed rule vs S0 | +1.12 [+0.30, +1.94] (i1) | +0.56 [-0.40, +1.51] |
| fixed rule vs the verdict flight's lock column | +1.47 [+0.23, +2.75] (i1) / +0.37 [-0.95, +1.71] (i2) | +1.12 [-0.31, +2.56] |
| non-empty contribution | -0.14 / -0.20 | -0.87 [-1.72, -0.06] |
| intent rows | 1 | 1 |
| criterion | - | NOT CONFIRMED |

**What it means.**

- VER-1 as registered under decision 258-A is not confirmed on Fold A. Decision 247's "stable" therefore fails for the
  rule. The Fold B in-sample +1.12 / +1.19 (n = 3) and +1.29 / +1.43 (n = 5) shrank to +0.56 on Fold A. That is 0.41 / 0.54 pp below
  the cross-fitted Fold B estimate (+0.97 / +1.10).
- The Fold A loss comes from non-empty-gold rows. With three samples, the 2-of-3 filter drops true entities (12 lost /
  5 gained), and the cross-flight verdict gate adds 6 more lost rows. The empty-gold gain (+1.37) is as large as on Fold B.
- One component holds on every 5-sample pool read: the support filter alone at n = 5, s = 2 over v4g (+0.76 .. +1.03, CI-LB
  > 0 on Fold B, a different Fold A pool and DEV). It is about +0.8 .. +1.0 pp at 6 contacts per row. That form was not
  flown on Fold A with the VER-1 base.
- The single-column c3 gate is positive in all five reads (+0.49 .. +0.98) but resolved in only three.

**What it does not mean.**

- It is DESCRIPTIVE on TRAIN folds (decisions 28 and 86). It is not a test claim, not a system-level claim, and not
  evidence about other carriers. The Fold A read is a confirmation of the rule's thresholds, not of the c3 template, which
  was authored from Fold A aggregate tables.
- It does not show that verification has no value. The oracle ceilings (+3.98 perfect gate, +5.34 best of 3 on Fold A;
  +8.77 best of 5 on Fold B) are far above every deterministic rule read. It shows that the measured deterministic rules
  convert little of that headroom.
- It admits nothing and changes nothing: lock v2.2 is untouched, and no `verification-delivery-v1` component exists.
  Whether VER-1 closes (260 A) or one more 5-sample Fold A pool flies (260 B) is decision 260, the owner's.

Methodological lesson, in one sentence: the confirmation flew the n = 3 form because it matched n = 5 only after
cross-fitting on Fold B, while the n = 3 filter on its own had already failed CI-LB > 0 on both earlier 5-sample pools
(ROLL-2 -0.07, ROLL-3 -0.71), so the form sent to confirmation was not the form that had replicated.

## 9. Pointers (sha256 of the on-file bytes read)

Analysis root `$SPEECHRL_DATA_DIR/analysis/`:

| file | sha256 |
| --- | --- |
| `SAEA-SLURP-VER1-OFFLINE-VER1A-FOLD-B/report.json` | `3679315c3022233a108766be0ee5332433fafa09f20fb62854d6177a3049d65b` |
| `SAEA-SLURP-VER1-OFFLINE-VER1A-FOLD-B/report.md` | `8652899218d479ea4d74eed3dce887736cdd322b96b504e2470b4101d901f2eb` |
| `SAEA-SLURP-VER1-OFFLINE-VER1B-FOLD-A-V1/report.json` | `8f1d47778420ca26a6ed4a22e961a223e04497ad94e818d37fc8898a8726437d` |
| `SAEA-SLURP-VER1-OFFLINE-VER1B-FOLD-A-V1/report.md` | `f9ac7b891aa9df2644ea177f4af764faa0d6677998d1c3c8c241781ede718f71` |
| `SAEA-SLURP-VER1-OFFLINE-CONTROLS-V2/report.json` / `report.md` | `da7f0cc63c002548674aabd53bd190c380dbabada0616598d0080ada855555a8` / `1246759c9170062d656d3f2d35d5db8bda87cd37b154f1ad7bee545c436d5bad` |
| `SAEA-SLURP-VER1-OFFLINE-ROLL2-FOLD-A-V2/report.json` / `report.md` | `b50328704b6a9a7e0d7b64929060bc780de798422d5520b7ace87c8aa120cc8d` / `79122757823cfabe15e8c38304555a24453a0e4767fd70c376e571480275736b` |
| `SAEA-SLURP-VER1-OFFLINE-ROLL3-DEV-V2/report.json` / `report.md` | `87a79e9e27ba11b4a3c1a2bd42468f2abb91bf50d5f4814536125b972051a58b` / `3eaba58e003d2eb49ef9044a3a0217873c726579d50da5e30700edf10280f5d5` |

VER-1c run `supply-variants/`:

| file | sha256 |
| --- | --- |
| `score-summary.json` | `7b149c8e3930ded1cb74e03cda8d7b61cb26c96f35de50beb296dc80ca59f458` |
| `render-manifest.json` | `07b0591383bc8cb5d6308dd578bbb741fadaf636731727e30639e77b1e7bd2ea` |
| `arm-lock-slurp-slu-official-train-scores.json` | `44a51be8baf5cbebdb0b624a644b990ff8e7e5f6ee362a01af8a8ce9bd5cd2a3` |
| `arm-aa-slurp-slu-official-train-scores.json` | `fcab5774d38ebe6e2941c223bdb8b89e694c404269fa9c62db8d781734331b2f` |
| `arm-r1-c3-slurp-slu-official-train-scores.json` | `a39da3a7901fb31f3cf13343b83850a10eaa9395c000e559f042ce7bcffdf346` |

Repository documents (sha256 at this note's base `5005a393d`):

| document | sha256 |
| --- | --- |
| `scripts/analysis/slurp_ver1_offline.py` | `356355175fe81a7a2b170f2263ea4cb6df5f058ba809217bc32854a3ae59ff15` |
| `tests/unit/test_slurp_ver1_offline.py` | `d14497af106fb5577034c53c7f569fc01d5ed13a6efafc2332cdddefb7ac133d` |
| composer README `docs/readiness/2026-10-10-slurp-ver1-offline-composer-v1/README.md` | `08aa8fb87984fce54014bac6ff3ff6ba7cf7ff989ef7b6249cdf9751c53b90da` |
| VER-1a README / `analysis-recipe-v1.json` | `6cdc486649ebd6b3a2708f6c402d0ababb92c7007ece54bdae630755d9f34f15` / `d0925b41175377fe1d64e85afe5e67ee6cd87acc65d5d9ae5a21a8b30c8b58b7` |
| VER-1b README / `analysis-recipe-v1.json` | `82d193cba7b37ecabb616613a414bb69436335ee66b588205ad77aa234fb9145` / `192258f4afa140bcc25ccf5857a89f07efd8d2364b92322841b0f38cd395a46b` |
| VER-1c README / `analysis-recipe-v1.json` | `5a26d37fd3d817412325064b6d19c567c19ec2456d4fbd54b475a20982ca10c8` / `fffc12fb1e126976911cf6e809d8f29a2bd52d788c2d329f511b64c1dc2af4bd` |
| registry `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md` | `7e0d0d6793a599f0f5e2e6e122b4b0a02bfe81e95afec30e919c6c0a63f0ec34` |
| `docs/exposure-ledger.md` | `1797435a89b010a2c680b885a6f478785126b4d0d2d6baf86bccd2c89034f361` |
| R6 offline note (the gate) `docs/results/2026-10-10-slurp-nx-r6-upstream-empty-decision-offline.md` | `cb45b6f44bd3656f957b6713f9ced42f974f3586ebb3d580d9a325f305dc10b1` |
| aggregation read (the support filter) `docs/results/2026-09-24-slurp-sample-aggregation-offline-read.md` | `0e9a180d5c2cd0a6395c59cb4287ec1f0e412b47ee470d56806f0b33020d669c` |
| ROLL-3 pool read `docs/results/2026-09-27-slurp-roll-3-dev2000-added-pool-read.md` | `91f43e4e400c5dc0d844fc78cf5df7e870be575021cdc6a59493d3e6b8f80991` |
| v4g lock note `docs/results/2026-10-09-slurp-postprocessing-v4g-lock-v1.md` | `e54bb33dd0f3e6113af3ba1737150fe0add8d03977d8324dd8024aeacbe874c6` |
| exchange-rate note `docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md` | `52e9525dc66b9246355bb8bf1e6c476723730fcd2ac3a2ba89dd1fb0190b23c6` |
| format model `docs/results/2026-10-10-slurp-nx-r6-perception-fold-b-column-read.md` | `3491a8cc1fdfdba8eeabb8509249ef7eae97a3deb9602018c2e3414e9e12c2c5` |

Reproduce, from the study root in WSL (`source ~/.venvs/speechrl/bin/activate`; `SPEECHRL_DATA_DIR` set). The composer is
model-free; its outputs are write-once, and `--no-write` prints the tables without writing.

```bash
python -B scripts/analysis/slurp_ver1_offline.py --mode read --run-id SAEA-SLURP-STAGE3-VER1B-SAMPLES-FOLD-A-V1 \
    --attempt attempt-slurp-native-stage3-ver1b-samples-fold-a-generation-v1 --split train --rows 1080 --n 3 --s 2 --thetas 0.2 \
    --verdict-run SAEA-SLURP-STAGE3-VER1C-C3-COLUMN-FOLD-A-V1:attempt-slurp-native-stage3-ver1c-c3-column-fold-a-generation-v1:r1-c3 \
    --label VER1B-FOLD-A-V1 --sealed-scorer slurp-slu-official-train --no-write
A=$SPEECHRL_DATA_DIR/analysis
sha256sum $A/SAEA-SLURP-VER1-OFFLINE-VER1A-FOLD-B/report.* $A/SAEA-SLURP-VER1-OFFLINE-VER1B-FOLD-A-V1/report.*
```
