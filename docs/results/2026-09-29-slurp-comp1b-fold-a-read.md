# Cell COMP-1b (COMP-1 minus the citation contract) paired read on TRAIN Fold A: intent +3.80 pp CI95 [+1.94, +5.65], official SLU-F1 -0.60 pp [-2.29, +1.07] against the in-chain A/A; zero-gold entity emission back to the A/A level (161 vs 162 rows) (DESCRIPTIVE)

Read on 2026-09-29 by the records and read agent (Claude Opus 5.5, on the coordinator's brief, Fable 5.1), in
worktree `fable/comp1bread`. The read is model-free. `core.flight.cli` and `lease_cli` were not invoked. There were
no model, server, encoder, embedder, tokenizer, scorer or GPU contacts. The read ran as a CPU sidecar while the
queue driver flew P-SV-1 seal-only.

The READ row `SAEA-SLURP-STAGE3-COMP1B-FOLD-A-PAIRED-ANALYSIS-V1` was root countersigned on master at `c17e92e0f`
(2026-09-29T20:45:34Z), after the seal and before any score was opened (owner decisions 189 option A and 198).

The recipe is `docs/readiness/2026-09-29-slurp-stage3-comp1b-fold-a-v1/analysis-recipe-v1.json` (recipe id
`slurp-stage3-comp1b-fold-a-paired-analysis-v1`). It is a paired row bootstrap: cluster key `sample_id`, 10,000
draws, seed 20260929.

No utterance text, gold label, slot filler, intent name as content or model output was printed or persisted. Only
counts, rates, pp, scenario names, ids and hashes appear below.

**DESCRIPTIVE.** These are development numbers on a TRAIN construction fold (owner decisions 28 and 86). They are
never a test claim or a generalisation claim. The verdict word belongs to the coordinator (decision 139).

## 1. What flew

| run | attempt | rows | contacts | speech s | prompt / completion tokens | GPU-h (monitor) | state |
| --- | --- | ---: | ---: | ---: | --- | ---: | --- |
| COMP-1b arm `SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1` | `attempt-slurp-native-stage3-comp1b-fold-a-generation-v1` | 1,080 | 4,360 | 12,454.691 | 38,366,462 / 259,372 | 1.7479 | COMPLETED, FINALIZED, clean tree |
| in-chain A/A `SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1` (reused cross-flight, decision 160) | `attempt-slurp-native-stage3-comp1-aa-fold-a-generation-v1` | 1,080 | 4,435 | 12,614.317 | 36,919,108 / 264,299 | 1.6786 | COMPLETED 2026-09-28 |

- **Flight.** The arm flew at commit `c6e98e6b` in the SAEA-Queue-NEXT chain (`queue_next.sh`), after a same-geometry
  serving restart at 18:50:26Z. The four-row smoke passed inspect at 18:51:39Z (never scored). The arm started
  18:51:49Z; its manifest was created 20:40:13Z; arm-inspect passed at 20:41:36Z with no fails, dirt empty, 1,080
  distinct rows, 0 tool calls and 11 finite-completion dispositions. The chain exited 0 at 20:41:56Z and the driver
  moved on to P-SV-1 seal-only at 20:43:01Z.
- **Seal hashes.** Run manifest `85609c73...945060a`, scores `35f4ff5e...3042d25`.
- **Contacts per row.** 4.037 (arm) vs 4.106 (A/A); the ceiling is 11. Per row the arm carries +1,340 prompt tokens
  (the agreement + centroid supply) and -4.6 completion tokens.

The registered driver `scripts/flights/read_paired_cell.sh` (through `comp1b_read.sh`) ran unchanged and wrote the
gating pass `vs-aa` (verdict `3e0da6a0...7959c1cd`). Its context pass stopped before writing any number: the recipe
names cell COMP-1's comparator attempt as `attempt-slurp-native-stage3-comp1-fold-a-generation-v1`, which never
sealed (COMP-1 sealed through its `-seal-only` attempt). The driver does not overwrite a pass directory, so the
context pass was re-run with the same driver core and the same arguments, with the left attempt set to the sealed
seal-only attempt, into `vs-comparator-sealonly/` (verdict `4f3d8229...9c0348ca`). The partial `vs-comparator/`
directory holds only the two driver copies and is kept as written.

## 2. The gating contrast: COMP-1b minus the in-chain A/A

| metric | A/A | COMP-1b | delta pp | CI95 pp | CI90 pp | saves / harms |
| --- | ---: | ---: | ---: | --- | --- | --- |
| **intent (scenario_action_exact), PRIMARY** | 81.85 | 85.65 | **+3.80** | **[+1.94, +5.65]** | [+2.22, +5.37] | 73 / 32 |
| **official pooled SLU-F1 (micro), GUARD** | 64.21 | 63.61 | **-0.60** | **[-2.29, +1.07]** | [-2.03, +0.80] | -- |
| span-F1 (micro) | 53.86 | 53.30 | -0.56 | [-2.51, +1.38] | [-2.19, +1.07] | -- |
| scenario exact | 87.31 | 89.17 | +1.85 | [+0.19, +3.52] | -- | 52 / 32 |
| action exact | 83.24 | 86.39 | +3.15 | [+1.39, +5.00] | -- | 68 / 34 |
| row SLU-F1 | 42.66 | 42.36 | -0.30 | [-1.63, +1.07] | -- | 75 / 85 |

The official scores are reproduced by the driver to 1e-6 on both arms. The unrounded CI95 bounds are intent
[+1.9444, +5.6481] and SLU-F1 [-2.2901, +1.0738]. McNemar p for intent is 7.8e-05.

| weighting | intent delta pp | intent CI95 | SLU-F1 delta pp | SLU-F1 CI95 |
| --- | ---: | --- | ---: | --- |
| natural mixture | +3.80 | [+1.94, +5.65] | -0.60 | [-2.29, +1.07] |
| equal scenario | +3.80 | [+1.94, +5.65] | -1.01 | [-2.98, +1.02] |

Recording channel (intent): far-field +4.13 (557 rows, 41 / 18), headset +3.44 (523 rows, 32 / 14). Row SLU-F1:
far-field -0.14, headset -0.47.

### Per stratum (60 rows each; delta pp, CI95 in brackets)

| scenario | A/A intent | COMP-1b intent | intent delta | SLU-F1 delta |
| --- | ---: | ---: | --- | --- |
| alarm | 90.00 | 93.33 | +3.33 [-3.33, +10.00] | -3.08 [-9.33, +3.02] |
| audio | 80.00 | 75.00 | -5.00 [-15.00, +5.00] | -4.14 [-19.40, +11.73] |
| calendar | 78.33 | 91.67 | +13.33 [+5.00, +21.67] | -3.75 [-9.35, +1.60] |
| cooking | 85.00 | 85.00 | 0.00 [-6.67, +6.67] | +7.58 [+0.85, +14.97] |
| datetime | 88.33 | 91.67 | +3.33 [0.00, +8.33] | +3.94 [-3.62, +12.57] |
| email | 85.00 | 90.00 | +5.00 [0.00, +11.67] | +2.90 [-2.58, +8.54] |
| general | 43.33 | 48.33 | +5.00 [-3.33, +13.33] | -15.54 [-33.29, -0.51] |
| iot | 88.33 | 83.33 | -5.00 [-13.33, +3.33] | -1.61 [-9.72, +5.78] |
| lists | 80.00 | 91.67 | +11.67 [+5.00, +20.00] | -7.47 [-17.66, +2.26] |
| music | 78.33 | 80.00 | +1.67 [-5.00, +8.33] | +1.35 [-4.77, +8.79] |
| news | 83.33 | 88.33 | +5.00 [-1.67, +13.33] | +5.29 [-1.39, +12.96] |
| play | 83.33 | 90.00 | +6.67 [0.00, +15.00] | -0.09 [-5.98, +5.79] |
| qa | 78.33 | 90.00 | +11.67 [+3.33, +21.67] | +7.46 [-0.22, +16.60] |
| recommendation | 91.67 | 96.67 | +5.00 [-1.67, +13.33] | -3.66 [-10.66, +3.28] |
| social | 73.33 | 85.00 | +11.67 [+3.33, +21.67] | -2.52 [-7.88, +2.97] |
| takeaway | 86.67 | 76.67 | -10.00 [-18.33, -1.67] | -3.10 [-8.29, +1.88] |
| transport | 86.67 | 88.33 | +1.67 [-5.00, +8.33] | -4.10 [-10.54, +1.56] |
| weather | 93.33 | 96.67 | +3.33 [0.00, +8.33] | +2.46 [-2.17, +7.42] |

Scenarios up / down / flat: intent 14 / 3 / 1; SLU-F1 7 / 11 / 0. Two per-stratum intervals exclude zero on the
harm side: intent on takeaway (-10.00) and SLU-F1 on general (-15.54). The general-scenario SLU loss is in the
scenario the 2026-09-24 general-scenario diagnostic already flagged; this read does not re-attribute it.

## 3. The context contrast: COMP-1b minus cell COMP-1 (the cited arm)

Context only, never the bar. Left = `SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1`, seal-only attempt.

| metric | COMP-1 | COMP-1b | delta pp | CI95 pp | saves / harms |
| --- | ---: | ---: | ---: | --- | --- |
| intent | 86.11 | 85.65 | -0.46 | [-1.30, +0.37] | 9 / 14 |
| official pooled SLU-F1 | 61.97 | 63.61 | **+1.64** | **[+0.38, +2.92]** | -- |
| span-F1 (micro) | -- | -- | +1.82 | [+0.29, +3.36] | -- |
| row SLU-F1 | 44.47 | 42.36 | -2.12 | [-3.27, -1.02] | 43 / 78 |

Removing the citation contract recovers pooled SLU-F1 (+1.64) at no measurable intent cost (-0.46, interval across
zero). Row-mean SLU-F1 moves the other way: under the contract more rows earn partial credit, while the pooled
count is dominated by the zero-gold false positives the contract added (section 4).

## 4. Entities: the attribution prediction check

Exact-match counts summed from the sealed per-sample `slot_f1_exact_*` fields (the A/A and COMP-1 rows reproduce
the attribution note's table exactly). 414 rows carry no gold entity; the count is identical on all three arms.

| arm | entity TP | FP | FN | emitted | FP on the 414 zero-gold rows | zero-gold rows emitting | official SLU-F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A/A | 530 | 497 | 411 | 1,027 | 186 | **162** | 64.21 |
| COMP-1b | 521 | 493 | 420 | 1,014 | 185 | **161** | 63.61 |
| COMP-1 | 538 | 611 | 403 | 1,149 | 288 | 252 | 61.97 |

Paired row bootstraps of the summed deltas (10,000 draws, seed 20260929):

| contrast | d FP all rows | d FP zero-gold rows | d zero-gold rows emitting |
| --- | --- | --- | --- |
| COMP-1b - A/A | -4 [-41, +31] | **-1 [-23, +20]** | -1 [-17, +15] |
| COMP-1b - COMP-1 | -118 [-149, -89] | -103 [-128, -79] | -91 [-110, -72] |

Against the recipe's step 5:

- **(a) zero-gold FP inside the same-bytes null [-27, +29]: HOLDS.** -1 [-23, +20]; 161 zero-gold rows emit vs the
  A/A's 162. The COMP-1 over-emission (+102) is gone entirely.
- **(b) official SLU-F1 no worse than -h_SLU (-1.2485): HOLDS on the point** (-0.60). The CI95 lower bound (-2.29)
  lies beyond -1.2485, so non-inferiority is not established by width.
- **(c) the same-shortlist intent-choice pattern:** not computed in this read (it needs the trace-level shortlist
  comparison of the attribution script, which is COMP-1-specific). The class table below carries the intent side.

The residual SLU gap is recall-side, not over-emission: TP -9 and FN +9 against the A/A with FP -4.

## 5. Delivery and the attribution classes

**Delivery (driver, gold on the scoring side only).** The row's gold intent boundary entry is delivered on 1,048 rows
under COMP-1b vs 947 under the A/A: 107 newly delivered, 6 newly lost. Of the 79 newly delivered rows the A/A
answered wrong, 36 convert to gold (45.6 %); 3 go right -> wrong. Transitions: delivered in both 941 rows (37
wrong -> right, 27 right -> wrong); newly delivered 107 (36 / 3); newly lost 6 (0 / 2). Boundary items per row: 8 on
1,078 rows.

**Attribution classes (owner decisions 138 and 152).** Over cell COMP-1's 191 PLAN intent-wrong rows, membership fixed
before contact in `docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1/attribution-classes-v1.json` (sha256
`28e78224...af323c0`). It applies unchanged: COMP-1b's prepared first-phase supply has output digest
`ce68bebc...e9c41a`, identical to COMP-1's.

| class | rows | gold delivered (prepared) | intent exact PLAN / A/A / COMP-1 / COMP-1b | wrong -> gold vs A/A | gold (A/A) -> wrong | both wrong: same / different |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| delivered-but-wrong | 86 | 82 | 0 / 9 / 33 / 35 | 30 | 4 | 31 / 16 |
| newly-by-both | 47 | 46 | 0 / 3 / 30 / 30 | 27 | 0 | 11 / 6 |
| newly-by-agree | 23 | 23 | 0 / 3 / 5 / 2 | 2 | 3 | 9 / 9 |
| newly-by-centroid | 8 | 6 | 0 / 1 / 3 / 3 | 2 | 0 | 1 / 4 |
| catch-all | 27 | 5 | 0 / 0 / 0 / 0 | 0 | 0 | 10 / 17 |
| **total** | **191** | **162** | **0 / 16 / 71 / 70** | **61** | **7** | 62 / 52 |

- **Newly delivered rows: 35 of 78 convert under COMP-1b (44.9 %)** vs 38 of 78 under COMP-1 (48.7 %). The
  difference sits in newly-by-agree (2 vs 5); newly-by-both converts identically (30 / 30).
- Delivery is not correctness: 43 of the 78 newly delivered rows stay wrong.

## 6. Byte and structure checks

- **Shared A/A.** Its prepared supply output digest is `ba5e1faa...fb54f`, the digest cell COMP-1's
  `shared-aa-proof-v1.json` established. The read opened its sealed manifest `c5cbcfbe...` and scores `59c32626...`.
- **Arm supply.** `prepared/SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1/phase-supply-v1.json` output digest `ce68bebc...`,
  equal to COMP-1's own arm supply, as the registration predicted (the contract never touches the first-phase
  supply). The driver's delivery stage checked both arms' `phases.json` seal pins.
- **Structure.** 0 tool schemas and 0 tool calls on both arms; deliver normaliser applied on 1,079 rows each;
  Planner REVISE 17 (arm) vs 44 (A/A), revisions executed 17 vs 40.
- **Official reproduction.** The driver reproduces both official SLU-F1 and span-F1 values to within 2e-16.

## 7. The rule and the verdict

The registered rule (protocol `slurp-stage3-comp1b-fold-a-protocol-v1`):

- ADMITTED: the intent CI95 lower bound above zero, the point at or above the declared 4.26 pp and the 2.5 pp
  cross-flight bar, AND the SLU-F1 guard holds.
- NEUTRAL: both guards non-inferior at the own null (h_intent 0.9943 / h_SLU 1.2485) without an admitted gain.
- HARMFUL: a measured loss on either guard (decision 25).

**Verdict (read agent, for the coordinator):**

- **Intent: a replicated composition gain below its declaration.** +3.80 [+1.94, +5.65]. The lower bound is above
  zero and the point clears the 2.5 pp cross-flight bar, but it is 0.46 pp under the declared 4.26. The ADMITTED
  branch is therefore not met on the point.
- **SLU-F1 guard: no measured loss, width not closed.** -0.60 [-2.29, +1.07]. The point sits inside -1.2485 and the
  upper bound is above zero, so the HARMFUL branch is not met. The lower bound is 1.04 pp beyond the margin, so
  non-inferiority, and with it the NEUTRAL branch, is not established by width.
- **The attribution prediction held.** Zero-gold emission returned to the A/A level (161 vs 162 rows; FP delta -1
  [-23, +20]), and against COMP-1 pooled SLU-F1 recovers +1.64 [+0.38, +2.92] at intent -0.46 [-1.30, +0.37].
- **On the coordinator's A2 bar** (intent CI lower bound > 0, point > 2.5, SLU guard held): the intent conditions
  hold; the SLU guard holds on the point with no measured loss and fails on the CI lower bound. That reads as
  **NOMINATED (intent), not ADMITTED**, with the SLU non-inferiority open on width. If the A2 registration proceeds,
  the declared expectation from this read is +3.80 pp.

Nothing is admitted. The coordinator's clause and the disposition are pending.

## 8. Reproduce

```bash
# model-free; master after the READ-row countersignature (c17e92e0f)
bash scripts/flights/comp1/comp1b_read.sh          # writes vs-aa; stops at vs-comparator (wrong comparator attempt)
# context pass on the sealed seal-only attempt (same driver core, same arguments otherwise)
PYTHONPATH=src python -B scripts/analysis/stage3_paired_read.py --stage3 --stage all \
  --left-run SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1 --left-attempt attempt-slurp-native-stage3-comp1-fold-a-generation-v1-seal-only \
  --right-run SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1 --right-attempt attempt-slurp-native-stage3-comp1b-fold-a-generation-v1 \
  --scorer-id slurp-slu-official-train --expected-split-role discovery --roster docs/receipts/rosters/slurp-evo-fold-a-v2.json \
  --cluster-key sample_id --split-identity-hash 61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6 \
  --seed 20260929 --draws 10000 --repo-root . --data-root "$SPEECHRL_DATA_DIR" \
  --analysis-root "$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-COMP1B-FOLD-A-PAIRED-ANALYSIS-V1/vs-comparator-sealonly"
PYTHONPATH=src python -B scripts/analysis/slurp_comp1b_read_supplement.py --repo-root . --data-root "$SPEECHRL_DATA_DIR" \
  --output "$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-COMP1B-FOLD-A-PAIRED-ANALYSIS-V1/supplement-v1.json"
```

Outputs under `analysis/SAEA-SLURP-STAGE3-COMP1B-FOLD-A-PAIRED-ANALYSIS-V1/`: `vs-aa/`, `vs-comparator-sealonly/`,
`supplement-v1.json` (sha256 `bdde064c...b1b486`); `attribution-classes-comp1b-v1.json` is an earlier in-session
run of the same class table (identical counts).

## Coordinator verdict (Fable 5.1, 2026-09-29)

- **COMP-1b (AGREE + centroid boundary key, no citation contract): NOMINATED on intent, not admitted.** Intent +3.80 [+1.94, +5.65] vs the in-chain A/A clears the 2.5 pp cross-flight bar on the point estimate with the lower bound above zero (0.46 pp under the declared 4.26); official SLU-F1 -0.60 [-2.29, +1.07] shows no measured loss (guard -1.2485 on the point). Development number (decisions 28/86).
- **Root cause confirmed by removal.** Against COMP-1, removing the citation contract gives SLU-F1 +1.64 [+0.38, +2.92] with intent -0.46 [-1.30, +0.37]; zero-gold rows emitting an entity return to the A/A level (161 vs 162; COMP-1 252). The citation contract is closed as a COMP-2 component (decision 198).
- **Admission test = A2.** COMP-1b's replication on DEV-2000-ADDED against its own in-chain A/A (registered held: `slurp-native-stage3-comp1b-dev2000-added-v1`, declared +3.80, guard h_SLU 1.2525) is the dev-admission read; on NOMINATED-or-better there, COMP-1b becomes the first composed component list of the consumption module (AGREE + centroid) and the test-sample milestone (decision 151) can be requested. Takeaway intent -10.0 and general SLU -15.5 (n = 60 strata) are noted for the DEV read's per-stratum table, not gated.
