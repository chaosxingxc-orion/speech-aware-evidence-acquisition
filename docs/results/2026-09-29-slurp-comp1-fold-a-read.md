# Cell COMP-1 (first composed arm: AGREE + centroid boundary key + citation contract) paired read on TRAIN Fold A, seal-only arm: intent +4.26 pp CI95 [+2.41, +6.11], official SLU-F1 -2.24 pp [-3.97, -0.47] against the in-chain A/A (DESCRIPTIVE)

Read on 2026-09-29 by Claude Fable 5.1, the records and read agent, in worktree `fable/comp1read`. The read is
model-free. `core.flight.cli` and `lease_cli` were not invoked. There was no model, server, encoder, embedder,
scorer, tokenizer or GPU contact. The G5 chain was flying on the GPU during the read, and this read ran beside it
as a CPU sidecar.

The READ row `SAEA-SLURP-STAGE3-COMP1-FOLD-A-PAIRED-ANALYSIS-V1` was root countersigned before contact on
2026-09-27. Its seal-only reading clause was countersigned on master at `cf38bec3b` on 2026-09-29T14:47:13Z. That
was after the seal and before any score was opened (owner decision 189 option A). The recipe is
`docs/readiness/2026-09-28-slurp-stage3-comp-1-fold-a-v1-resume-v1/analysis-recipe-v1.json`, recipe id
`slurp-stage3-comp1-fold-a-resume-paired-analysis-v1`. It uses a paired row bootstrap with cluster key
`sample_id`, 10,000 draws, seed 20260927, and TRAIN gold through `slurp-slu-official-train`.

No utterance text, gold label, slot filler, intent name or model output was printed or persisted. Only counts,
rates, scenario names, ids and hashes appear below.

**DESCRIPTIVE.** These are development numbers on a TRAIN construction fold (owner decisions 28 and 86). They are
never a test claim or a generalisation claim. The verdict word belongs to the coordinator (decision 139).

## 1. What flew and what was sealed

The arm run `SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1` was sealed through attempt
`attempt-slurp-native-stage3-comp1-fold-a-generation-v1-seal-only`:

- **Flight and state.** Queue `queue_sealonly.sh`, flight commit `fd8a01fe`. The run manifest was created
  2026-09-29T14:42:12Z and is COMPLETED. The attempt is FINALIZED. `study_repo_dirt` is empty.
- **Rows.** 1,080 rows: 471 kept from the original attempt (trace `029a2dbb...61997`) and 609 kept from resume
  attempt 3 (trace `87be5cef...3df26`). 0 rows were flown and there were 0 new contacts.
- **Scoring.** One official finalize score job, 0 failed.
- **Next step.** The G5 campaign started at 14:46:23Z.
- **Seal hashes (sha256).**
  - run manifest: `19249b72c33915169a3f256c9e79143173a98e5d0881a7ac3c97246f6e30bae3`
  - outputs: `98b9494e0d93dc92545dca747f39d6cfa682439f24e228d1d7e3dad6cf37b119`
  - scores: `af567f9abfafef77b19307c091171db6de4b2e9b0bb081d24dbfc2ef89f7ac40`

| run | rows | contacts | speech s | prompt / completion tokens | GPU-h | state |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| COMP-1 arm, the two contributing attempts (original + resume 3) | 1,080 | 4,389 (1,913 + 2,476) | 12,564.262 | 38,876,164 / 347,522 | n/a (no serving monitor on aborted attempts); contact-summed server time 7.040 h at np4 | seal-only COMPLETED |
| COMP-1 arm, run-cumulative spend incl. resume 1 and 2 (no row kept) | -- | 4,441 (1,913 + 4 + 48 + 2,476) | 12,694.112 | -- | -- | caps 11,880 calls |
| in-chain A/A `SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1` | 1,080 | 4,435 | 12,614.317 | 36,919,108 / 264,299 | 1.6786 (monitor) | COMPLETED 2026-09-28 |

The arm's GPU-h cannot be read from a serving monitor. The two aborted attempts sealed no `seal` stage, and the
seal-only attempt served nothing. The contact-summed llama-server compute (`prompt_ms + predicted_ms` over the
wire responses of the two contributing traces: 2.928 h + 4.111 h) overstates wall GPU time at np4 concurrency.
For comparison, the A/A's own contact-summed compute would be the like-for-like figure; it was not computed here.

## 2. How the read ran (two read-path gaps, both disclosed)

1. The registered driver `scripts/flights/read_paired_cell.sh`, run on the resume package at master `cf38bec3b`,
   **refused** before opening any score. The seal-only attempt has no `<run>.generation-manifest.json`, because
   it flies 0 rows and `core.flight.cli seal-only` writes none. The refusal left
   `analysis/SAEA-SLURP-STAGE3-COMP1-FOLD-A-PAIRED-ANALYSIS-V1/vs-aa/` holding only the two copied driver
   files. That directory was left untouched.
2. The same driver bytes were then run unchanged against a scratch **mirror data root**
   (`/home/chao/comp1read-mirror`). The mirror symlinks every sealed file and adds one clearly labelled stand-in
   `generation-manifest.json`. The stand-in carries the seal-only run manifest's own zero cost. It is copied
   beside the output as `synthesized-generation-manifest.json`, sha256 `94a62e36...74971f3`.
   - The generation manifest feeds only the driver's cost and frontier fields. Those fields are therefore
     **not** read for the arm (they show 0). Section 1 gives the real spend.
   - Output base: `analysis/SAEA-SLURP-STAGE3-COMP1-FOLD-A-PAIRED-ANALYSIS-V1/seal-only-mirror-read/`.
   - The driver wrote its score contrasts, per-scenario tables, structural summary and efficiency, then
     **stopped** at its phase stage. A seal-only attempt also seals no `phases.json`.
   - The gating contrast was fully written before that stop.
   - Output hashes:
     - `vs-aa/score-contrasts.json`: `6c238048e7fc85e5f96322ad05a958e43757ac6ef08dcd1ea107a1af7524b0d8`
     - `vs-aa/per-scenario-tables.json`: `edab73a3fa6f725aa07f2ac2560b902e28dfc098d0afc7740509f843724f6390`
     - `vs-aa/structural.json`: `ec54532f806345b38a86cc0576ff3dab51665afff794db0a67f3d17bc5c177ad`
     - `vs-comparator/score-contrasts.json` (context pass, same stop): `52371d4260eae3ee18582febb4387167e06cb41b484188c29cdee29db0d15d6e`
3. The recipe steps the driver does not reach are computed by the new model-free script
   `scripts/analysis/slurp_comp1_sealonly_read_supplement.py` into `seal-only-mirror-read/supplement-v1.json`
   (sha256 `70d683e4b5334e8bcb2a0bbeca8456c684373c75d02f1b68a0ee538e32936fc6`). Those steps are:
   - step 5, the attribution table and the harm split;
   - step 6, the listed rows;
   - a Solver-side delivery proxy for step 2;
   - the entity over-emission split;
   - part of step 7;
   - the predecessor spend.

Byte checks:

- **Official reproduction.** The driver's official-reproduction check passes on both arms: SLU-F1 micro recomputed
  vs official differs by 0.0 on the arm and by 1.1e-16 on the A/A.
- **Scorer identity.** The scorer's identity check passed on the arm.
- **Replay proof.** The seal-only replay proof (`SAEA-SLURP-STAGE3-COMP1-FOLD-A-SEALONLY-REPLAY-PROOF-V1`) checked
  1,080 rows, with 0 failing and 0 sealed twice.
- **Predecessor traces.** The manifest's predecessor trace hashes equal the registered ones (`029a2dbb...`,
  `87be5cef...`).

## 3. The gating contrast: arm vs the in-chain A/A (n = 1,080 paired rows)

| metric | A/A | COMP-1 | delta pp | CI95 | saves / harms |
| --- | ---: | ---: | ---: | --- | --- |
| **intent (scenario_action exact), PRIMARY** | 81.85 | 86.11 | **+4.26** | **[+2.41, +6.11]** | 76 / 30 |
| **official pooled SLU-F1, GUARD** | 64.21 | 61.97 | **-2.24** | **[-3.97, -0.47]** (half-width 1.75) | -- |
| official pooled span-F1 | 53.86 | 51.48 | -2.38 | [-4.35, -0.41] | -- |
| action exact | 83.24 | 86.94 | +3.70 | [+1.94, +5.56] | 72 / 32 |
| scenario exact | 87.31 | 89.72 | +2.41 | [+0.74, +4.07] | 57 / 31 |
| per-row mean SLU-F1 | 42.66 | 44.47 | +1.82 | [+0.44, +3.20] | 94 / 73 |
| per-row slot F1 exact | 35.14 | 36.24 | +1.09 | [-0.39, +2.56] | 62 / 55 |

Equal-scenario weighting gives intent +4.26 [+2.50, +6.11] and SLU-F1 -4.13 [-6.08, -2.20]. Scenarios up / down /
flat: intent 12 / 3 / 3, SLU-F1 7 / 11 / 0.

The per-row SLU-F1 mean and the official pooled SLU-F1 move in opposite directions. Section 5 explains why: the
arm emits more entities, which adds pooled false positives.

The context pass against the sealed locked PLAN arm is never the bar. PLAN scores intent 82.22 and SLU-F1 63.63.
COMP-1 vs PLAN: intent +3.89 [+2.13, +5.74], official pooled SLU-F1 -1.66 [-3.44, +0.11].

Per-scenario table (60 rows each, CI95 in brackets):

| scenario | intent A/A -> COMP-1 | intent delta [CI95] | SLU-F1 A/A -> COMP-1 | SLU-F1 delta [CI95] |
| --- | --- | --- | --- | --- |
| alarm | 90.00 -> 93.33 | +3.33 [-3.33, +10.00] | 75.64 -> 69.88 | -5.76 [-12.87, +1.33] |
| audio | 80.00 -> 76.67 | -3.33 [-13.33, +6.67] | 66.52 -> 25.48 | **-41.04 [-56.87, -26.23]** |
| calendar | 78.33 -> 90.00 | +11.67 [+3.33, +21.67] | 67.61 -> 64.27 | -3.34 [-8.94, +2.08] |
| cooking | 85.00 -> 85.00 | 0.00 [-5.00, +5.00] | 57.42 -> 63.11 | +5.69 [-0.49, +12.89] |
| datetime | 88.33 -> 91.67 | +3.33 [0.00, +8.33] | 71.34 -> 74.93 | +3.59 [-4.08, +11.94] |
| email | 85.00 -> 90.00 | +5.00 [0.00, +11.67] | 62.49 -> 62.93 | +0.43 [-6.29, +6.64] |
| general | 43.33 -> 48.33 | +5.00 [-5.00, +15.00] | 32.56 -> 15.09 | **-17.46 [-34.16, -2.74]** |
| iot | 88.33 -> 86.67 | -1.67 [-10.00, +5.00] | 67.06 -> 64.37 | -2.69 [-9.82, +3.86] |
| lists | 80.00 -> 90.00 | +10.00 [+3.33, +18.33] | 58.60 -> 49.77 | -8.84 [-16.26, -1.53] |
| music | 78.33 -> 78.33 | 0.00 [-6.67, +6.67] | 47.85 -> 39.75 | -8.10 [-15.87, -0.41] |
| news | 83.33 -> 86.67 | +3.33 [-3.33, +10.00] | 64.27 -> 67.40 | +3.13 [-3.76, +10.60] |
| play | 83.33 -> 90.00 | +6.67 [+1.67, +13.33] | 54.50 -> 51.89 | -2.61 [-10.25, +4.58] |
| qa | 78.33 -> 93.33 | +15.00 [+5.00, +25.00] | 59.98 -> 65.58 | +5.61 [-1.57, +13.93] |
| recommendation | 91.67 -> 100.00 | +8.33 [+1.67, +16.67] | 71.20 -> 69.65 | -1.56 [-8.76, +5.81] |
| social | 73.33 -> 88.33 | +15.00 [+5.00, +26.67] | 59.32 -> 56.72 | -2.59 [-8.60, +3.18] |
| takeaway | 86.67 -> 78.33 | -8.33 [-18.33, +1.67] | 61.55 -> 62.21 | +0.66 [-4.05, +5.27] |
| transport | 86.67 -> 86.67 | 0.00 [-8.33, +8.33] | 69.13 -> 65.58 | -3.55 [-10.09, +2.92] |
| weather | 93.33 -> 96.67 | +3.33 [0.00, +8.33] | 75.82 -> 79.95 | +4.13 [-1.52, +10.83] |

Recording strata (the driver's `per_channel` table):

| stratum | n | intent delta pp (saves / harms) | per-row SLU-F1 delta pp (saves / harms) |
| --- | ---: | --- | --- |
| far-field | 557 | +4.31 (42 / 18) | +2.91 (58 / 38) |
| headset | 523 | +4.21 (34 / 12) | +0.65 (36 / 35) |

## 4. Attribution classes (owner decisions 138 and 152)

The table covers the 191 PLAN intent-wrong rows. Membership was fixed before contact.

| class | rows | gold delivered (prepared) | intent exact PLAN / A/A / COMP-1 | wrong -> gold vs A/A | gold (A/A) -> wrong | both wrong: same / different intent |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| delivered-but-wrong | 86 | 82 | 0 / 9 / 33 | 29 | 5 | 28 / 20 |
| newly-by-both | 47 | 46 | 0 / 3 / 30 | 27 | 0 | 11 / 6 |
| newly-by-agree | 23 | 23 | 0 / 3 / 5 | 5 | 3 | 7 / 8 |
| newly-by-centroid | 8 | 6 | 0 / 1 / 3 | 2 | 0 | 0 / 5 |
| catch-all | 27 | 5 | 0 / 0 / 0 | 0 | 0 | 9 / 18 |
| **total** | **191** | **162** | **0 / 16 / 71** | **63** | **8** | 55 / 57 |

Conversion against the declared basis:

- Of the 78 newly delivered rows, 38 convert to gold under COMP-1: **48.7 %**.
- The declared basis was 56 of 125 pooled (0.448), which predicted 34.9 rows = 3.23 pp.
- The realised 38 rows are worth 3.52 pp against PLAN.
- Per class:

  | class | converted | rate |
  | --- | ---: | ---: |
  | newly-by-both | 30 / 47 | 63.8 % |
  | newly-by-agree | 5 / 23 | 21.7 % |
  | newly-by-centroid | 3 / 8 | 37.5 % |

- Single-factor rates for comparison: CONV 32 / 70 (45.7 %) and KPROBE 24 / 55 (43.6 %).
- The already-delivered-but-wrong class also converts 33 / 86 under COMP-1, against 9 / 86 under the A/A.

Harm split over the 888 rows that PLAN scores intent-correct:

| bank class | rows | wrong under COMP-1 | wrong under A/A |
| --- | ---: | ---: | ---: |
| CORRECT | 480 | 12 | 7 |
| ENTITY-MIXED | 193 | 11 | 7 |
| ENTITY-FN-ONLY | 84 | 2 | 2 |
| ENTITY-FP-ONLY | 131 | 5 | 5 |
| total | 888 | 30 | 21 |

The bank's one MALFORMED row is in neither set.

Step 6 rows, by id (intent exact PLAN / A/A / COMP-1):

| row | class | PLAN / A/A / COMP-1 |
| --- | --- | --- |
| unseeded `slurp:train:015793:audio-1490106752` | catch-all | 0 / 0 / 0 |
| `slurp:train:000116:audio-1434537220` | delivered-but-wrong | 0 / 0 / 0 |
| `slurp:train:000215:audio-1502200839` | delivered-but-wrong | 0 / 0 / 0 |
| `slurp:train:010011:audio-1498483953` | delivered-but-wrong | 0 / 0 / 0 |
| `slurp:train:010212:audio-1501150440-headset` | delivered-but-wrong | 0 / 1 / 0 |
| `slurp:train:013443:audio-1498567184` | newly-by-both | 0 / 0 / 0 |
| `slurp:train:015237:audio-1502195173` | newly-by-centroid | 0 / 0 / 0 |
| `slurp:train:015351:audio-1434532573-headset` | newly-by-centroid | 0 / 0 / 0 |

The last seven rows (after the unseeded one) are the rows that lose delivery under the composition.

**Delivery check (step 2), proxy only.** On all 191 intent-wrong rows, the Solver's recorded `supplied_value_ids`
contain the row's gold boundary value id exactly where the membership file predicts delivery: 162 of 191, agreeing
on 191 of 191. Over the whole roster it is 1,048 of 1,080.

Two parts of the registered check were not run:

- the Perception phase's own flown consumption, which lives in the predecessor traces;
- the A/A-equals-locked-plan (86) half. The A/A's Solver carries no citation record, so it has no proxy.

The pre-flight shared-A/A proof (`shared-aa-proof-v1.json`, verdict IDENTICAL, supply digest `ba5e1faa...` on all
1,080 rows) stands for that half.

## 5. Where the SLU-F1 guard is lost

The pooled official entity counts, COMP-1 vs A/A:

| count | A/A | COMP-1 | change |
| --- | ---: | ---: | ---: |
| entity TP | 530 | 538 | +8 |
| entity FP | 497 | 611 | **+114** |
| entity FN | 411 | 403 | -8 |
| emitted entities | 1,027 | 1,149 | +122 |

Row-level emission:

- 180 rows emit more entities under COMP-1 and 62 emit fewer.
- Rows whose gold has no entity but whose delivered answer emits one: **252 vs 162 (+90)**.
- The span-FP increase is concentrated by scenario:

  | scenario | span-FP change |
  | --- | ---: |
  | audio | +30 |
  | music | +15 |
  | recommendation | +15 |
  | lists | +14 |
  | general | +13 |
  | cooking | -11 |
  | datetime | -6 |

So the guard loss is **over-emission**, not lost recall. On the Solver, the element new to COMP-1 relative to the
A/A and to the single-factor AGREE and KPROBE arms is the cited-answer contract. Its deliver normaliser changed
1,080 / 1,080 rows on the arm, against 90 / 1,080 on the A/A. That makes the contract the leading suspect, but this
read does not isolate it: that is a hypothesis for the coordinator, not an attribution.

Citation envelope on the arm (step 7, partial):

- 1,105 Solver contacts, parse `ok` on 1,105 / 1,105.
- finish `stop` on 1,105 / 1,105.
- 1,790 cited ids in total.

Not emitted by this read (outstanding):

- the per-entry citation credit table;
- the per-contact token delta against the A/A;
- the frontier row.

## 6. Against the registered decision rule

The rule is fixed in `docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1/protocol-registered-v1.json`.
The declared expected effect is 3.23 pp intent. The cross-flight in-chain A/A bar is 2.5 pp at n = 1,080. The
own-null margins are h_intent 0.9943 and h_SLU 1.2485.

- **Intent primary.** +4.26 pp, CI95 [+2.41, +6.11]. The lower bound is above zero, and the point clears both the
  declared 3.23 pp and the 2.5 pp bar. The lower bound (+2.41) sits 0.09 pp under the 2.5 bar.
- **SLU-F1 guard.** -2.24 pp, CI95 [-3.97, -0.47]. The whole interval is below zero, and the point is beyond
  -h_SLU (-1.2485). This is a measured loss on the guard (decision 25).
- **Branches.** The ADMITTED branch needs the guard to hold, and it does not. The rule's HARMFUL branch ("a
  measured loss on either guard") is met.

**Verdict (read agent, for the coordinator): the numbers fall in the HARMFUL branch on the official SLU-F1 guard
(-2.24 [-3.97, -0.47], entity over-emission +114 FP), while the intent primary clears its declared effect (+4.26
[+2.41, +6.11] vs 3.23 declared, 2.5 bar). The attribution table shows the two retrieval factors compose as
declared on intent (newly-by-both converts 30 / 47, above either single factor). The conflict sits on the slot side
and is not located by this read.** Under owner decision 138, no further element is admitted on top of this
unresolved conflict. The verdict word and its disposition are the coordinator's (decision 139).

## Coordinator verdict (Fable 5.1, 2026-09-29)

- **COMP-1: NOT ADMITTED** (HARMFUL on the official SLU-F1 guard, -2.24 [-3.97, -0.47]); the intent composition (+4.26 [+2.41, +6.11]) is confirmed. Cause named by `2026-09-29-slurp-comp1-slu-harm-attribution.md`: the Solver cited-answer contract adds entities on zero-gold rows (+102 of the +114 false positives); the I7n unwrap and the AGREE/centroid supply are cleared. Next cell COMP-1b (AGREE + centroid, no citation contract) on the same roster vs the same A/A (owner decision 198); the citation contract leaves the COMP-2 component list. Development number (decisions 28/86).
