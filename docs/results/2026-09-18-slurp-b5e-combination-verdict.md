# Cell B5e: the early combination of modules M1 and M4b on the sealed anchor, TRAIN A

Status: **BAR NOT MET on the official number (62.34 / 80.09); combination HARMFUL.** Cell B5e reads
**62.3351** official pooled SLU-F1 and **80.0926** official intent. The intent bar (78.00) is
cleared by 2.09 pp; the SLU bar (64.00) is missed by **1.66 pp**, so clause 1 as amended by owner
decision 23 does not pass. Against the sealed cell B1 arm the combination gains
**+1.1957 pp** pooled SLU with a CI95 of **[-0.1134, +2.4819]** -- a lower bound that does not clear
zero -- and its intent is a dead tie, **-0.0926 pp**, 26 saves against 27 harms, exact two-sided
McNemar p = 1.000, but with a CI95 of **[-1.5136, +1.3788]** whose **lower bound lies below
-h_intent = -1.0051**. Clause 3 is written on that bound, so it fires and the mechanical status is
**HARMFUL**: the v2 candidate falls back to B1 alone, **B5er is not registered**, and the owner is
told. Section "The rule, applied unchanged" records, without softening the clause, that the trigger
fires on **interval width rather than on a measured intent loss**. Root: the B5e paired-read agent,
2026-09-18. Program: `docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md` (section 4,
the B5 form). Preregistration:
`docs/readiness/2026-09-18-slurp-b5e-combination-v1-preregistration.md`, with clause 1 replaced
before any number existed by
`docs/readiness/2026-09-18-slurp-b5e-combination-v1-amendment-decision-23.md` (owner decision 23:
the bar reads the **official unprojected** `evaluate.py` number), and the one root-diagnosed recovery
recorded in `docs/readiness/2026-09-18-slurp-b5e-combination-v1-recovery-v1.md`. Margins: the TRAIN A
own null of cell B0r, **h_SLU = 1.1218 pp** and **h_intent = 1.0051 pp** at CI95
(`docs/results/2026-09-17-slurp-b0-review-off-redecision-v2.md`).

## What flew

One attempt, the cell's **one allowed recovery**: a full re-fly of all 1,080 rows after the first
arm aborted at 25 contacts on 2026-09-18T14:40:20Z when the coordinator's own `powercfg` change
tripped the scheduled tasks' stop-on-battery condition and killed the resident server. The aborted
run `SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-V1` is closed, was never
scored and was never read; its 25 calls are charged to it and not to this run. **No rows were
resumed**: item E10 was not merged when this cell flew, and recovering 25 of 11,880 contacts did not
pay, so every one of the 1,080 rows in this manifest was flown fresh as one complete manifest.

Run `SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1`, attempt
`attempt-slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-generation-recovery-v1`,
FINALIZED, manifest **COMPLETED** at study commit `281cee7c4e624357e8edf1f9497cdb075876485d`,
composed config `50ae44a67e1d6e897e266f9ebadb4eead62df091d4f4fbc72b9a8100b1f28ae1`, protocol
`b5d14e1fe060ee9f2b7ccc6d174b4e16cd82b5b07a9d9850808d2656ecfee4c0` -- the values the recovery
registration pinned -- arm `speech-feature-query-native-tools`, profile `bounded-discovery-probe`,
split identity `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, role `discovery`,
attached to the resident session `serving-slurp-native-candidate-five-train-a-np4-v1`, one official
complete scoring job.

The two factors against the sealed dual-store anchor live in one channel, `knowledge_stores`:
**M1** adds the `train-exemplars` store byte-for-byte as cell B1's recovery arm flew it (release
`171aa4a8...`, snapshot `4c498dc0...`, plain top-k = 20, `saea-fuse-supplyfilter-v1` at
m = c = top_l = 20, tau 0.0, keyed by the row's own sealed full-utterance speech vector), and
**M4b** re-pins `slot-contracts` from v1 to v2 byte-for-byte as cell B4b flew it (release
`f8e42d4f...`, snapshot `d5992bd1...`). The role graph, every instruction template, the Perception
retrieval geometry, the roster, the split, the model fragment and the np4 / 24,576-token geometry are
the anchor's. That the M1 channel is identical is not asserted here but measured: **on 1,080 of 1,080
rows cell B5e's twenty supplied exemplar value ids are exactly cell B1's twenty** (mean overlap 20.0
of 20).

Rows: 1,080 scored per arm; parsed **1,079 B5e**, 1,079 B4b, 1,076 B1, 1,073 anchor, 1,080 direct.

### Provenance

| Artifact | SHA-256 |
| --- | --- |
| B5e `scores.json` | `aeed7ad9b7fe44e74c4b9e65470e0d96429637ccaa4655c9185515568a70d7b9` |
| B5e `run-manifest.json` | `1d827e31bd26e65e1327ec8c81dc96ebb55cd470692b339ab5323fcea1c86808` |
| B5e `outputs.jsonl` | `3d861012bfbbf267d47023d069e5ccfe0442a3212cb3bd855e100eb8475751a6` |
| B5e `trace.jsonl` | `523a1d11422133278bf0dec3672808828e5b7ab75be95138c2ed704c81e6ae10` |
| B5e `flight-receipts.json` | `b27c4faa6ccde041aa870f1693cbfa595f27b55ab61d5f0185b38c2321be1be3` |
| B1 arm `scores.json` | `a7105b328509a8bd00c4678fd076e9be4d242b6189bb82bbd290bd596e3c9078` |
| B1 arm `run-manifest.json` | `b07ed553ff9f78b8e3ead6797bb66fb92a1820793b8aa5061576c6f66aa1a8ad` |
| B1 arm `outputs.jsonl` | `db9cd6329b0837d8f120f153556c951a68969da167d245d695eb35916237deca` |
| B1 arm `trace.jsonl` | `874a91a8ef1729289cde6c3164d9a834bbe702cda9075a6e84155b5b688aba8a` |
| B4b `scores.json` | `751c529806e7cd03db13cfba58d583bf7b9d7f14b5b62b6b26e676a5acb308a1` |
| B4b `run-manifest.json` | `b3f7e7ac0babd5ae3e764ad93948203cc40192d72ac3a156b4a479cc69c256ea` |
| B4b `outputs.jsonl` | `01b56d39fa55c48fbdf53e9e9ad5ac4b92428bd9d13a8308a958a7aa0048dfdb` |
| anchor `scores.json` | `7360876322488e5fda689fcafda00e90da2ebf559e5a35e635c550f940202b47` |
| anchor `run-manifest.json` | `049ac230e536bc6c8fe45bc847756ba486c4904e9c7602c698157f78d70c0152` |
| anchor `outputs.jsonl` | `d87d71e8fa0fe93b45d5c6817ba125b016d8d91f44a14309171dd0f3a64270d8` |
| anchor `trace.jsonl` | `912e9853e2e32afec9a009afd0aecdae696f6299343f22d3613f4edcde2c6e67` |
| direct anchor `scores.json` | `7840a959fe4f43928fda0e0cacfe8c0ee4200116bfcd269bfe3451b59da29c38` |
| direct anchor `run-manifest.json` | `546109055a373b358c43d36878c532b95784ee5d73d07f011c5fa3ea3d7ce11e` |
| direct anchor `outputs.jsonl` | `5c182ddfc81effe2465fb58f052842538f22ead3601355dbe77427c937decd61` |
| roster `docs/receipts/rosters/slurp-evo-fold-a-v2.json` | `1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d` |
| roster metadata | `07f4cd83b83d83d65500a328e0a38421ede575195c63ae118def0d1006c14e34` |
| exemplar release (pinned) | `171aa4a82c2b15fff2c72e907ea80298be8d72309cca0d7367eb50debb042129` |
| exemplar snapshot: declared content hash / file bytes | `4c498dc0282055b9fe036ed7e950af519bd48b5f26e76876d0250727196a72e9` / `fcb5506c63653abe996dea15fdccd7c81a84a837b6377ca13f5b35d73283d6b2` |
| paired read `analysis/SAEA-SLURP-B5E-COMBINATION-PAIRED-ANALYSIS-V1/score-contrasts.json` | `9ce5678666b50e411f9530693907017d3285f156a6d1a586ad60271dc12d8d7c` |
| paired read `.../README.md` | `b7e0d63559f66f61ca3eb05a941a96b8421c9b7af0e20926a5c763bbb6986266` |
| paired read driver `.../b5e_paired_read.py` | `0f5a60a8eb15c2ae641718c817ea103d2b456a17dd94ba3a4c9ae63db737db59` |
| paired read `.../per-scenario-tables.json` | `ccef9924ff31b04cd22882b41589153e77ec61df79bf54f8041ee6d537f29089` |
| paired read `.../m1-diagnostics.json` | `cc37650795438f6fc2f23a531756498dc04c16e5df72727100e9f7bfbc0b5d03` |
| paired read `.../m4b-slot-diagnostics.json` | `7a9103e75895749e4c6f8ab9de5dc857b23394e70814bc76944a87b9c86ee01b` |
| paired read `.../interaction.json` | `cd685ed43cc73803c46ebaf914b94ed53b8b3bf431f30df767c565cf0e44418d` |

Every hash above was recomputed from the file before it was read. The driver is an adapted copy of
three sealed precedent drivers whose estimator calls are reproduced byte for byte:
`analysis/SAEA-SLURP-B1-EXEMPLARS-K20-PAIRED-ANALYSIS-V1/b1_paired_read.py`
(`2644710aee90b62fa200aed847ddfda2544e776f4f59c57853e4fc7dd4479225`),
`analysis/SAEA-SLURP-B1-TWIN-PAIRED-ANALYSIS-V1/b1_twin_paired_read.py`
(`f8b14341bfaa3bfaca701c86d7e1cd06cdfa395483141a8aa0b407c153fef932`) and
`analysis/SAEA-SLURP-B4B-SLOT-STORE-V2-PAIRED-ANALYSIS-V1/b4b_paired_read.py`
(`80d6db58da00bfe1f48d4e2240d2e837bdb4300df3c9b08f02f14c1fa9258ce2`). Only the arm list, the contrast
list, the additivity stage and the decision block are new; `analysis.null_calibration_cli.rows_for`,
`analysis.null_calibration.pooled_f1`, `analysis.paired.resampled_statistic` and
`analysis.paired.paired_contrast` are unchanged. Paired whole-speaker cluster bootstrap over the
roster's 125 speakers, 10,000 draws, seed 20260915, CI95 for advancement and CI90 for diagnostics as
percentiles of the same retained replicate sequence; sensitivity the paired scenario-stratified row
bootstrap (18 scenarios of 60) on the same draws and seed.

### The conditional fifth comparator is dropped

The analysis recipe admitted `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-REPLICATE-V2`, the
B4b request-identical replicate, **only if it sealed before this cell's first contact**. It did not:
its first attempt aborted and its resume-recovery attempt
(`...-generation-v2-resume`) was in flight while this read ran, so the run directory holds no run
manifest and no official score. **It is named here and left out, and it never gates.**

## The STOP condition, closed before any B5e table was read

The four registered comparator aggregates and, additionally, **both sealed single-module verdict
tables** were recomputed from the sealed bytes and required to agree before the B5e contrasts were
opened. **PASSED**, with zero failures.

Registered aggregates, all reproduced to better than 0.005 pp: anchor 48.53 / 77.96 / 84.81 / 79.26 /
29.50; B1 61.14 / 80.19 / 86.39 / 81.39 / 48.43; B4b 51.09 / 78.52 / 85.09 / 79.63 / 32.40; direct
33.89 / 73.70 / 82.69 / 75.09 / 21.10. Under projection v3: 51.99 / 79.35, 62.67 / 81.76,
54.05 / 79.72 and 34.31 / 75.37. Under the TRAIN symmetric scorer: 52.09 / 41.38, 62.97 / 54.51,
54.26 / 43.99 and 34.46 / 24.38.

| Contrast | Metric | Verdict | Recomputed | Verdict CI95 | Recomputed CI95 |
| --- | --- | ---: | ---: | --- | --- |
| B1 minus anchor | Official pooled SLU-F1 | 48.53 -> 61.14, +12.61 | 48.5336 -> 61.1394, +12.6058 | [+10.54, +14.60] | [+10.5381, +14.5983] |
| B1 minus anchor | Intent | 77.96 -> 80.19, +2.22 | 77.9630 -> 80.1852, +2.2222 | [+0.74, +3.71] | [+0.7407, +3.7073] |
| B1 minus anchor | Pooled span F1 | 29.50 -> 48.43, +18.93 | 29.4976 -> 48.4286, +18.9311 | [+15.93, +21.76] | [+15.9268, +21.7635] |
| B4b minus anchor | Official pooled SLU-F1 | 48.53 -> 51.09, +2.55 | 48.5336 -> 51.0855, +2.5519 | [+1.13, +3.98] | [+1.1294, +3.9770] |
| B4b minus anchor | Intent | 77.96 -> 78.52, +0.56 | 77.9630 -> 78.5185, +0.5556 | [-0.71, +1.82] | [-0.7117, +1.8182] |
| B4b minus anchor | Pooled span F1 | 29.50 -> 32.40, +2.91 | 29.4976 -> 32.4034, +2.9059 | [+0.79, +5.12] | [+0.7850, +5.1162] |

The recipe's own four-digit STOP values reproduce exactly: **+10.5381 / +0.7407** for B1 minus anchor
and **+1.1294 / -0.7117** for B4b minus anchor. Saves / harms / ties reproduce exactly on every
per-row metric of both verdicts (B1: intent 43 / 19 / 1,018, scenario 28 / 11 / 1,041, action
42 / 19 / 1,019, exact slot F1 213 / 38 / 829, row SLU-F1 276 / 63 / 741; B4b: 24 / 18 / 1,038,
16 / 13 / 1,051, 22 / 18 / 1,040, 63 / 38 / 979, 112 / 58 / 910). The registered v3 and symmetric
contrasts reproduce too: B1 minus anchor v3 **+10.67 [+8.55, +12.77]** and symmetric **+10.89
[+8.72, +13.00]**; B4b minus anchor v3 **+2.06 [+0.53, +3.51]** and symmetric **+2.17
[+0.62, +3.68]**.

## B5e minus the cell B1 arm -- the gating contrast (percentage points)

| Metric | B1 | B5e | Delta | Speaker CI95 | Speaker CI90 | Scenario-stratified CI95 | Equal-scenario |
| --- | ---: | ---: | ---: | --- | --- | --- | ---: |
| Official pooled SLU-F1 | 61.14 | 62.34 | **+1.20** | [-0.11, +2.48] | [+0.10, +2.28] | [-0.16, +2.56] | +1.12 |
| Intent (scenario+action) | 80.19 | 80.09 | **-0.09** | [-1.51, +1.38] | [-1.29, +1.12] | [-1.39, +1.20] | -0.09 |
| Scenario | 86.39 | 86.39 | 0.00 | [-0.98, +1.02] | [-0.81, +0.85] | [-1.11, +1.02] | 0.00 |
| Action | 81.39 | 81.39 | 0.00 | [-1.42, +1.49] | [-1.20, +1.24] | [-1.30, +1.30] | 0.00 |
| Pooled span F1 | 48.43 | 49.82 | +1.39 | [-0.41, +3.12] | [-0.11, +2.84] | [-0.40, +3.22] | +1.22 |
| Exact slot F1 (row mean) | 31.35 | 31.94 | +0.59 | [-0.67, +1.84] | [-0.45, +1.63] | [-0.64, +1.82] | +0.59 |
| SLU-F1 (row mean) | 40.15 | 41.01 | +0.86 | [-0.22, +1.91] | [-0.05, +1.76] | [-0.22, +1.95] | +0.86 |

Saves / harms / ties with the exact two-sided McNemar p: intent 26 / 27 / 1,027 (**1.000**); scenario
17 / 17 / 1,046 (1.000); action 26 / 26 / 1,028 (1.000); exact slot F1 49 / 41 / 990 (0.461); row
SLU-F1 76 / 67 / 937 (0.504). **Not one of the seven intervals excludes zero at CI95, and not one of
the five sign tests rejects.** On the three label metrics the two arms are indistinguishable to the
row: scenario and action are exactly equal (86.3889 and 81.3889 on both arms), and intent differs by
one row in 1,080. Turning M4b on inside the combination moves slots a little -- pooled SLU +1.20,
span F1 +1.39, exact slot F1 +0.59 -- and moves labels not at all. At CI90 the pooled SLU interval
does clear zero ([+0.10, +2.28]); the registered clause reads CI95 and is applied as registered.

## B5e minus the sealed anchor -- what both modules buy together

| Metric | Anchor | B5e | Delta | Speaker CI95 | Speaker CI90 | Scenario-stratified CI95 | Equal-scenario |
| --- | ---: | ---: | ---: | --- | --- | --- | ---: |
| Official pooled SLU-F1 | 48.53 | 62.34 | **+13.80** | [+11.77, +15.80] | [+12.09, +15.46] | [+11.91, +15.71] | +13.24 |
| Intent (scenario+action) | 77.96 | 80.09 | **+2.13** | [+0.90, +3.32] | [+1.09, +3.12] | [+0.65, +3.61] | +2.13 |
| Scenario | 84.81 | 86.39 | **+1.57** | [+0.54, +2.52] | [+0.71, +2.38] | [+0.46, +2.78] | +1.57 |
| Action | 79.26 | 81.39 | **+2.13** | [+0.86, +3.27] | [+1.08, +3.10] | [+0.65, +3.61] | +2.13 |
| Pooled span F1 | 29.50 | 49.82 | **+20.32** | [+17.35, +23.19] | [+17.82, +22.74] | [+17.36, +23.29] | +19.23 |
| Exact slot F1 (row mean) | 19.02 | 31.94 | **+12.91** | [+10.87, +14.93] | [+11.20, +14.61] | [+10.93, +15.02] | +12.91 |
| SLU-F1 (row mean) | 30.29 | 41.01 | **+10.71** | [+9.12, +12.30] | [+9.37, +12.04] | [+9.15, +12.31] | +10.71 |

Saves / harms / ties: intent 45 / 22 / 1,013 (**6.74e-3**); scenario 30 / 13 / 1,037 (**1.37e-2**);
action 45 / 22 / 1,013 (**6.74e-3**); exact slot F1 215 / 30 / 835 (**1.15e-35**); row SLU-F1
281 / 49 / 750 (**1.09e-40**). Every metric clears zero and the scenario-stratified sensitivity agrees
on every row. **The combination is a large, unambiguous gain over the base it was built on** -- it is
only against its own stronger leg that it cannot be separated.

### Additivity, reported and never a gate (owner decision 23)

| Metric | B5e minus anchor | B1 minus anchor | B4b minus anchor | Sum | Interaction | Interaction CI95 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Official pooled SLU-F1 | +13.8015 | +12.6058 | +2.5519 | +15.1577 | **-1.3562** | [-3.29, +0.56] |
| Intent | +2.1296 | +2.2222 | +0.5556 | +2.7778 | -0.6481 | [-2.42, +1.14] |
| Scenario | +1.5741 | +1.5741 | +0.2778 | +1.8519 | -0.2778 | [-1.65, +1.08] |
| Action | +2.1296 | +2.1296 | +0.3704 | +2.5000 | -0.3704 | [-2.15, +1.43] |
| Pooled span F1 | +20.3208 | +18.9311 | +2.9059 | +21.8370 | -1.5161 | [-4.31, +1.25] |
| Exact slot F1 (row mean) | +12.9144 | +12.3278 | +1.6019 | +13.9297 | -1.0152 | [-2.77, +0.78] |
| SLU-F1 (row mean) | +10.7143 | +9.8548 | +1.6924 | +11.5472 | -0.8330 | [-2.38, +0.71] |

The interaction is defined exactly as registered -- the bootstrap of
`B5e - anchor - (B1 - anchor) - (B4b - anchor)`, i.e. `B5e - B1 - B4b + anchor`, over the paired rows
under the same resampler, seed and draws.

**The additive sum +15.16 pp lies INSIDE the (B5e minus anchor) CI95 [+11.77, +15.80]**, close to its
upper edge, so additivity is not rejected at CI95. The point estimate nevertheless falls **1.36 pp
short** of the sum, and the interaction is **negative on all seven metrics** without being bounded
away from zero on any of them: the honest reading is a consistent but unproven sub-additivity, which
is exactly the outcome the preregistration named as expected rather than defective. In v3 terms the
same statement holds: (B5e minus anchor) v3 = **+11.78 [+9.63, +13.88]** against the v3 additive sum
of +12.73, again inside. Owner decision 23's rule is satisfied by reporting this and gating nothing
on it. As a point-estimate decomposition, M1 accounts for 91.3 % of the combination's gain over the
anchor and M4b for 18.5 %, the 9.8 % excess being the interaction.

## B5e minus cell B4b -- M1's contribution inside the combination (reported, never gating)

| Metric | B4b | B5e | Delta | Speaker CI95 | Speaker CI90 | Scenario-stratified CI95 | Equal-scenario |
| --- | ---: | ---: | ---: | --- | --- | --- | ---: |
| Official pooled SLU-F1 | 51.09 | 62.34 | **+11.25** | [+9.26, +13.23] | [+9.57, +12.90] | [+9.35, +13.18] | +11.13 |
| Intent (scenario+action) | 78.52 | 80.09 | **+1.57** | [+0.30, +2.92] | [+0.50, +2.68] | [+0.28, +2.87] | +1.57 |
| Scenario | 85.09 | 86.39 | **+1.30** | [+0.23, +2.31] | [+0.41, +2.15] | [+0.28, +2.41] | +1.30 |
| Action | 79.63 | 81.39 | **+1.76** | [+0.47, +3.04] | [+0.69, +2.81] | [+0.46, +3.06] | +1.76 |
| Pooled span F1 | 32.40 | 49.82 | **+17.41** | [+14.49, +20.30] | [+14.94, +19.82] | [+14.41, +20.37] | +16.69 |
| Exact slot F1 (row mean) | 20.62 | 31.94 | **+11.31** | [+9.33, +13.34] | [+9.62, +12.98] | [+9.32, +13.36] | +11.31 |
| SLU-F1 (row mean) | 31.99 | 41.01 | **+9.02** | [+7.44, +10.65] | [+7.70, +10.38] | [+7.50, +10.56] | +9.02 |

Saves / harms / ties: intent 36 / 19 / 1,025 (**3.00e-2**); scenario 26 / 12 / 1,042 (**3.36e-2**);
action 36 / 17 / 1,027 (**1.27e-2**); exact slot F1 192 / 35 / 853 (**1.99e-27**); row SLU-F1
246 / 63 / 771 (**1.07e-26**). Evaluated under the same three clauses, **all three pass**: the pooled
SLU CI95 lower bound is +9.26 > 0, the intent CI95 lower bound is +0.30 > -1.0051, and no scenario's
intent CI95 upper bound lies below zero. **M1's contribution inside the combination is large and
survives every clause; M4b's does not separate from noise.** This contrast does not gate, and it is
reported as registered.

## B5e minus the released direct anchor (secondary, never a gate)

Pooled SLU **+28.45** [+25.11, +31.76]; intent +6.39 [+4.34, +8.51]; scenario +3.70 [+1.48, +6.01];
action +6.30 [+4.08, +8.61]; pooled span F1 +28.72 [+24.84, +32.58]; exact slot F1 row mean +21.22
[+18.71, +23.79]; row SLU-F1 +24.95 [+22.60, +27.47]. Saves / harms: intent 134 / 65
(p = 1.13e-6), row SLU-F1 418 / 48 (p = 9.41e-75). The system-over-direct margin on pooled SLU grows
from the anchor's +14.65 to **+28.45**. One honest note carried forward, as the B1 and twin verdicts
carried theirs: against the **direct** anchor owner decision 17's diagnostic flags `general`
(net harmed +5); no scenario loses intent beyond the band on this or any other contrast. The band is
a clause of the rule only against **cell B1**.

## The rule, applied unchanged

| Clause | Requirement | Value | Threshold | Passes |
| --- | --- | ---: | ---: | --- |
| 1 (amended, owner decisions 1 and 23) | official unprojected pooled SLU-F1 >= 64.00 | **62.3351** | 64.00 | **NO** |
| 1 (amended) | official intent (scenario+action) >= 78.00 | **80.0926** | 78.00 | **YES** |
| 1 -- **MEETS THE BAR** | both of the above | -- | -- | **NO** |
| 2a, combination | CI95 lower bound of (B5e - B1) pooled official SLU > 0 | **-0.1134** | 0 | **NO** |
| 2b, combination | (B5e - B1) intent CI95 lower bound > -1.0051 | **-1.5136** | -1.0051 | **NO** |
| 2c, combination | no scenario's paired intent CI95 upper bound against B1 below zero | 0 of 18 breaching | CI95 upper < 0 | **YES** |
| 2 -- combination **ADMITTED** | 2a and 2b and 2c | -- | -- | **NO** |
| 3a, HARMFUL | (B5e - B1) pooled SLU CI95 **upper** bound < -1.1218 | +2.4819 | -1.1218 | no |
| 3b, HARMFUL | (B5e - B1) intent CI95 **lower** bound < -1.0051 | **-1.5136** | -1.0051 | **YES -- FIRES** |
| Additivity (reported, not a gate) | additive sum +15.16 against the (B5e - anchor) CI95 | [+11.77, +15.80] | -- | inside |

**Status: the bar is NOT MET and the combination is HARMFUL by clause 3.** Read once, from the single
official score of the complete manifest; no repeat, no re-score, no row filtering.

**The honesty note this clause needs, and the verdict does not soften the clause to avoid it.**
Clause 3's second disjunct is a *non-inferiority* statement written on the CI95 lower bound, and here
it fires on an arm whose intent is a **dead tie**: 80.1852 against 80.0926, a difference of one row
in 1,080, 26 saves against 27 harms, exact two-sided McNemar p = 1.000, with a symmetric interval
[-1.51, +1.38] whose *upper* bound is just as far above +1.0051 as its lower bound is below -1.0051.
The trigger therefore records **interval width, not a measured loss**. The width has a structural
cause worth stating before this clause is reused: **h_intent = 1.0051 was measured by cell B0r
against cell B0 on byte-identical requests**, the tightest pairing the program can construct, whereas
B5e and B1 differ in one knowledge store and their trajectories diverge row by row under greedy
decoding that is not bitwise reproducible across batch compositions. A margin calibrated on a
request-identical null is systematically narrower than the interval any real one-factor contrast on
this roster can produce, so on a true tie the clause fires roughly whenever the contrast's own CI95
half-width exceeds 1.0051 pp -- here it is 1.446 pp. **The clause is applied exactly as registered and
the status stands**; the program should decide, before clause 3 is reused, whether the HARMFUL
trigger ought to require a negative point estimate as well as a bound below the margin.

**Consequences, both branches, taken together.**

- **Clause 3's own consequence (preregistration section 7):** the v2 candidate **falls back to B1
  alone**, **B5er is NOT registered**, and **the owner is told**. This verdict is that telling.
- **Owner decision 20 (the bar branch):** the bar is **not lowered**. Admission continues in owner
  decision 15's order -- **keep admitting B2 v3, B7a and B4a** (B4c only if B4a admits) -- and
  **B5b**, the combination of every module admitted by then, is read against the same bar of 64.00 /
  78.00. Only if B5b also misses does the owner re-decide between a lower bar and a core-swap study.
- Owner decision 19's meeting branch -- register B5er, then lock "SLURP base v2.0" on two passes --
  is **not reached**.
- **Module M4b's provisional status is untouched.** Its replication branch is owner decision 13's
  request-identical replicate, whose resume-recovery is in flight; this read is a combination read and
  a non-separating `(B5e minus B1)` contrast is neither a replication nor a refutation of cell B4b's
  own admitted effect.

## Every scenario, B5e minus B1 (natural mixture; equal-scenario mean in the last row)

| Scenario | n | B1 SLU | B5e SLU | Delta | B1 intent | B5e intent | Delta | Intent CI95 | Net harmed | Flag | Beyond band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | --- |
| alarm | 60 | 65.28 | 72.87 | +7.60 | 81.67 | 88.33 | +6.67 | [+0.00, +11.91] | -4 | no | no |
| audio | 60 | 60.35 | 59.88 | -0.47 | 78.33 | 83.33 | +5.00 | [+0.00, +12.90] | -3 | no | no |
| calendar | 60 | 64.16 | 63.41 | -0.75 | 78.33 | 76.67 | -1.67 | [-7.46, +3.70] | +1 | no | no |
| cooking | 60 | 64.74 | 64.52 | -0.22 | 88.33 | 86.67 | -1.67 | [-5.66, +0.00] | +1 | no | no |
| datetime | 60 | 69.80 | 71.41 | +1.61 | 88.33 | 90.00 | +1.67 | [+0.00, +5.26] | -1 | no | no |
| email | 60 | 57.93 | 65.29 | +7.36 | 83.33 | 88.33 | +5.00 | [+0.00, +10.34] | -3 | no | no |
| general | 60 | 20.41 | 17.42 | **-2.99** | 43.33 | 38.33 | **-5.00** | [-13.12, +3.64] | +3 | no | no |
| iot | 60 | 64.30 | 66.75 | +2.45 | 88.33 | 88.33 | 0.00 | [+0.00, +0.00] | +0 | no | no |
| lists | 60 | 53.45 | 59.44 | +6.00 | 85.00 | 86.67 | +1.67 | [+0.00, +5.36] | -1 | no | no |
| music | 60 | 48.87 | 47.67 | -1.19 | 78.33 | 73.33 | **-5.00** | [-10.94, +0.00] | +3 | no | no |
| news | 60 | 60.85 | 59.67 | -1.19 | 83.33 | 81.67 | -1.67 | [-5.77, +0.00] | +1 | no | no |
| play | 60 | 49.94 | 54.45 | +4.51 | 60.00 | 61.67 | +1.67 | [-13.46, +14.93] | -1 | no | no |
| qa | 60 | 58.16 | 59.17 | +1.02 | 75.00 | 75.00 | 0.00 | [+0.00, +0.00] | +0 | no | no |
| recommendation | 60 | 68.67 | 67.05 | -1.62 | 90.00 | 90.00 | 0.00 | [-5.00, +4.84] | +0 | no | no |
| social | 60 | 57.33 | 55.84 | -1.49 | 75.00 | 71.67 | -3.33 | [-8.33, +0.00] | +2 | no | no |
| takeaway | 60 | 60.43 | 56.97 | **-3.46** | 85.00 | 83.33 | -1.67 | [-5.08, +0.00] | +1 | no | no |
| transport | 60 | 62.79 | 65.52 | +2.73 | 90.00 | 85.00 | **-5.00** | [-10.00, +0.00] | +3 | no | no |
| weather | 60 | 73.93 | 74.10 | +0.17 | 91.67 | 93.33 | +1.67 | [+0.00, +5.41] | -1 | no | no |
| **equal-scenario mean** | 18 | | | **+1.12** | | | **-0.09** | | | | |

Ten scenarios up and eight down on pooled SLU, the extremes `alarm` +7.60 and `email` +7.36 against
`takeaway` -3.46 and `general` -2.99. **No scenario loses intent beyond the band and none reaches
owner decision 17's five-row flag**; the worst net figures are +3 on `general`, `music` and
`transport`. The equal-scenario weighting (+1.12 SLU, -0.09 intent) agrees with the natural mixture
(+1.20, -0.09), so the non-separation is not a single-stratum artifact.

## Every scenario, B5e minus the sealed anchor

| Scenario | n | Anchor SLU | B5e SLU | Delta | Anchor intent | B5e intent | Delta | Intent CI95 | Net harmed | Flag | Beyond band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | --- |
| alarm | 60 | 52.66 | 72.87 | **+20.21** | 83.33 | 88.33 | +5.00 | [-1.47, +14.63] | -3 | no | no |
| audio | 60 | 47.75 | 59.88 | +12.12 | 76.67 | 83.33 | +6.67 | [-2.86, +15.38] | -4 | no | no |
| calendar | 60 | 48.38 | 63.41 | +15.04 | 75.00 | 76.67 | +1.67 | [-3.45, +7.94] | -1 | no | no |
| cooking | 60 | 62.47 | 64.52 | +2.05 | 85.00 | 86.67 | +1.67 | [+0.00, +5.45] | -1 | no | no |
| datetime | 60 | 59.52 | 71.41 | +11.90 | 83.33 | 90.00 | +6.67 | [+1.67, +12.70] | -4 | no | no |
| email | 60 | 36.64 | 65.29 | **+28.66** | 85.00 | 88.33 | +3.33 | [+0.00, +8.47] | -2 | no | no |
| general | 60 | 15.45 | 17.42 | +1.97 | 36.67 | 38.33 | +1.67 | [-3.70, +7.14] | -1 | no | no |
| iot | 60 | 55.53 | 66.75 | +11.22 | 86.67 | 88.33 | +1.67 | [+0.00, +5.36] | -1 | no | no |
| lists | 60 | 43.55 | 59.44 | +15.90 | 83.33 | 86.67 | +3.33 | [+0.00, +8.62] | -2 | no | no |
| music | 60 | 34.53 | 47.67 | +13.14 | 76.67 | 73.33 | -3.33 | [-10.30, +3.08] | +2 | no | no |
| news | 60 | 44.24 | 59.67 | +15.43 | 80.00 | 81.67 | +1.67 | [+0.00, +5.77] | -1 | no | no |
| play | 60 | 46.82 | 54.45 | +7.62 | 58.33 | 61.67 | +3.33 | [-11.11, +16.39] | -2 | no | no |
| qa | 60 | 57.04 | 59.17 | +2.14 | 75.00 | 75.00 | 0.00 | [+0.00, +0.00] | +0 | no | no |
| recommendation | 60 | 49.75 | 67.05 | +17.31 | 90.00 | 90.00 | 0.00 | [-6.78, +6.56] | +0 | no | no |
| social | 60 | 34.74 | 55.84 | **+21.10** | 66.67 | 71.67 | +5.00 | [+0.00, +11.11] | -3 | no | no |
| takeaway | 60 | 48.84 | 56.97 | +8.14 | 85.00 | 83.33 | -1.67 | [-5.08, +0.00] | +1 | no | no |
| transport | 60 | 51.34 | 65.52 | +14.19 | 86.67 | 85.00 | -1.67 | [-5.63, +0.00] | +1 | no | no |
| weather | 60 | 53.81 | 74.10 | **+20.29** | 90.00 | 93.33 | +3.33 | [+0.00, +8.62] | -2 | no | no |
| **equal-scenario mean** | 18 | | | **+13.24** | | | **+2.13** | | | | |

**All eighteen scenarios gain on pooled SLU**, from `general` +1.97 to `email` +28.66. No scenario
loses intent beyond the band and none reaches the decision-17 flag.

## Every scenario, B5e minus cell B4b

| Scenario | n | B4b SLU | B5e SLU | Delta | B4b intent | B5e intent | Delta | Intent CI95 | Net harmed | Flag | Beyond band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | --- |
| alarm | 60 | 65.76 | 72.87 | +7.11 | 88.33 | 88.33 | 0.00 | [-3.33, +6.25] | +0 | no | no |
| audio | 60 | 47.32 | 59.88 | +12.56 | 78.33 | 83.33 | +5.00 | [-3.23, +11.67] | -3 | no | no |
| calendar | 60 | 52.06 | 63.41 | +11.36 | 75.00 | 76.67 | +1.67 | [+0.00, +5.36] | -1 | no | no |
| cooking | 60 | 61.76 | 64.52 | +2.76 | 86.67 | 86.67 | 0.00 | [-4.62, +4.84] | +0 | no | no |
| datetime | 60 | 64.31 | 71.41 | +7.10 | 88.33 | 90.00 | +1.67 | [-5.56, +8.62] | -1 | no | no |
| email | 60 | 41.19 | 65.29 | **+24.10** | 86.67 | 88.33 | +1.67 | [+0.00, +5.26] | -1 | no | no |
| general | 60 | 12.50 | 17.42 | +4.92 | 31.67 | 38.33 | +6.67 | [+1.56, +12.96] | -4 | no | no |
| iot | 60 | 59.02 | 66.75 | +7.74 | 85.00 | 88.33 | +3.33 | [+0.00, +8.33] | -2 | no | no |
| lists | 60 | 37.81 | 59.44 | **+21.63** | 83.33 | 86.67 | +3.33 | [+0.00, +8.62] | -2 | no | no |
| music | 60 | 36.07 | 47.67 | +11.60 | 78.33 | 73.33 | **-5.00** | [-10.94, +0.00] | +3 | no | no |
| news | 60 | 48.90 | 59.67 | +10.77 | 80.00 | 81.67 | +1.67 | [+0.00, +5.77] | -1 | no | no |
| play | 60 | 50.85 | 54.45 | +3.59 | 63.33 | 61.67 | -1.67 | [-14.00, +10.29] | +1 | no | no |
| qa | 60 | 54.98 | 59.17 | +4.19 | 73.33 | 75.00 | +1.67 | [+0.00, +5.56] | -1 | no | no |
| recommendation | 60 | 51.12 | 67.05 | +15.94 | 85.00 | 90.00 | +5.00 | [-1.75, +12.50] | -3 | no | no |
| social | 60 | 40.65 | 55.84 | +15.19 | 66.67 | 71.67 | +5.00 | [+0.00, +11.11] | -3 | no | no |
| takeaway | 60 | 49.14 | 56.97 | +7.84 | 83.33 | 83.33 | 0.00 | [-4.76, +4.62] | +0 | no | no |
| transport | 60 | 52.14 | 65.52 | +13.38 | 86.67 | 85.00 | -1.67 | [-5.63, +0.00] | +1 | no | no |
| weather | 60 | 55.51 | 74.10 | **+18.59** | 93.33 | 93.33 | 0.00 | [+0.00, +0.00] | +0 | no | no |
| **equal-scenario mean** | 18 | | | **+11.13** | | | **+1.57** | | | | |

All eighteen scenarios gain on pooled SLU. No scenario loses intent beyond the band; none reaches the
decision-17 flag.

## Projection v3 and the TRAIN symmetric view, beside the rule

Owner decision 23 moved the bar onto the official unprojected number; projection v3 (owner decision
7) and the TRAIN symmetric sibling (owner decision 14) are reported here as diagnostics and move no
verdict. Each arm's sealed `outputs.jsonl` was COPIED under the analysis directory and the registered
scorers read the copy. All four comparators reproduce their registered readings exactly, which is
what licenses reading B5e's numbers beside them.

| Arm | v3 SLU | v3 intent | v3 scenario | v3 action | v3 span F1 | Labels / fillers changed |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| anchor | 51.99 | 79.35 | 85.46 | 80.65 | 40.30 | 20 / 195 |
| B4b | 54.05 | 79.72 | 85.93 | 80.83 | 41.85 | 21 / 170 |
| B1 | 62.67 | 81.76 | 87.13 | 82.96 | 52.65 | 24 / 90 |
| **B5e** | **63.78** | **81.85** | **87.31** | **83.15** | **53.55** | 31 / **80** |
| direct | 34.31 | 75.37 | 84.17 | 75.93 | 23.24 | 47 / 36 |

**Would projection v3 have cleared 64.00? NO.** The v3-projected pooled SLU-F1 is **63.7757**, which
is **0.22 pp below the bar** -- and 0.95 pp below the 64.73 that owner decision 19's additive
arithmetic predicted from 62.67 + 2.06. The v3 intent, 81.85, clears 78.00 comfortably. So the cell
misses the bar under *both* readings, and decision 23's change of metric is not what decided it: the
gap on the official scale is 1.66 pp and on the v3 scale 0.22 pp. v3 contrasts: **B5e - B1 SLU +1.11
[-0.31, +2.56]**, intent +0.09 [-0.99, +1.14], span F1 +0.90 [-0.84, +2.71]; **B5e - anchor SLU
+11.78 [+9.63, +13.88]**, intent +2.50 [+1.42, +3.58]; **B5e - B4b SLU +9.72 [+7.63, +11.93]**;
B5e - direct SLU +29.46 [+26.09, +32.81]. The filler-normalisation counts fall monotonically with the
entity story -- anchor 195, B4b 170, B1 90, **B5e 80** -- so the combination needs the least
projection repair of any arm on this base.

| Arm | Official pooled SLU | Symmetric pooled SLU | Gap | Official span F1 | Symmetric span F1 | False merges |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| anchor | 48.53 | 52.09 | +3.56 | 29.50 | 41.38 | 34 |
| B4b | 51.09 | 54.26 | +3.18 | 32.40 | 43.99 | 34 |
| B1 | 61.14 | 62.97 | +1.83 | 48.43 | 54.51 | 34 |
| **B5e** | **62.34** | **64.18** | **+1.84** | **49.82** | **55.73** | 34 |
| direct | 33.89 | 34.46 | +0.57 | 21.10 | 24.38 | 34 |

Symmetric contrasts: **B5e - B1 SLU +1.20 [-0.22, +2.65]**, intent -0.09 [-1.51, +1.38], span F1
+1.23 [-0.62, +3.04]; **B5e - anchor SLU +12.09 [+9.96, +14.22]**; **B5e - B4b SLU +9.91
[+7.79, +12.15]**. **Every gating sign agrees with the unprojected view and no interval changes its
verdict.** One number deserves to be said out loud and then set aside: on the symmetric scale B5e
reads **64.18**, which would clear 64.00 -- but the symmetric scorer is not the bar under any owner
decision, its representation-alignment credit (+1.84 pp) is exactly the charge the official metric
levies for writing a filler differently from the corpus, and quoting it as a pass would be
substituting a friendlier metric for the community-standard one that decision 23 chose.

## The mandatory M1 diagnostics

The instrument is each arm's own sealed trace -- the first-Perception response projected through
`rails.slurp_intent_hypotheses.project_bounded_slurp_intent_hypotheses`, the flight's own recorded
`train-exemplars` value ids, and each arm's sealed delivered answer -- exactly the instrument cells B1
and B1-twin used. **It reproduces every one of the cell B1 verdict's arm and anchor readings.**

| Diagnostic | B5e | B1 arm | Anchor |
| --- | ---: | ---: | ---: |
| Supplied exemplars per row | 20 on 1,080 / 1,080; **4,990** distinct values of 9,354 | 20 on 1,080 / 1,080; 4,990 distinct | -- |
| Rows whose supplied set is identical to B1's | **1,080 / 1,080** (mean overlap 20.0 of 20) | -- | -- |
| Gold intent among the arm's own Perception candidates | 936 (0.8667) | 939 (0.8694) | 937 (0.8676) |
| Delivered intent among the arm's own candidates | 1,040 (0.9630) | 1,044 (0.9667) | 1,051 (0.9731) |
| Delivered intent correct | **865 (0.8009)** | 866 (0.8019) | 842 (0.7796) |
| Solver escape to a neighbour intent | **7 rows (0.65 %)**, **7 of 7 onto gold** | 6 rows (0.56 %), 5 onto gold | -- |
| Delivered intent outside candidates and exemplars | 33 | 30 | -- |
| Delivered intent present among the twenty exemplar intents | 976 | 979 | -- |
| **Candidate-union coverage realised** | **0.9722** (1,050 / 1,080) | 0.9722 | 0.8676 candidates only |
| A2 recovery set available through this arm's exemplars | 113 rows | 113 rows | -- |
| ... delivered correctly | **11 of 113** | 10 of 113 | 0 of 113 |
| Intent echo (neighbour plurality equals the delivered intent) | 0.7222 | 0.7241 | -- |
| Gold filler recall among the twenty | 0.5770 (543 / 941) | 0.5770 (543 / 941) | -- |
| Gold type recall among the twenty | 0.9590 | 0.9590 | -- |
| Delivered mentions echoing a supplied exemplar filler | **489 of 986 (0.4959)** | 500 of 1,000 (0.5000) | 265 of 910 (0.2912) |
| Gold-exact mentions | **509** | 501 | 340 |

**Candidate-union coverage is realised at exactly A2's predicted 0.9722**, identical to cell B1's,
which is the direct consequence of the measured fact above: the supply is the same supply. The
recovery set is the same 113 rows and the combination converts **11** of them against B1's 10 and the
anchor's 0. The escape-to-neighbour-intent rate is 7 rows (0.65 %) against B1's 6 (0.56 %), and
**every one of B5e's seven escapes landed on gold** against B1's five of six. Gold-exact mentions rise
to 509, the best of any arm on this base.

**Exemplar token volume per row** is, as it must be, identical to cell B1's: mean **1,874.45**
characters, p50 1,807, p95 2,696, max **3,232** (468.6 / 674.0 / 808.0 chars-over-4 proxy tokens), all
inside the preregistration's section-9 rendered-block maximum of 4,332 characters (1,083 proxy
tokens). The exemplar supply is acquired **exactly once per row on 1,080 of 1,080 rows**.

Review loop:

| Quantity | B5e | B1 arm | Anchor |
| --- | ---: | ---: | ---: |
| Rows with a Planner REVISE token | 7 | 7 | 5 |
| Rows with a second Solver visit (revisions executed) | 7 | 7 | 5 |
| Rows whose intent changed across the revision | **7** | 3 | 2 |
| Planner token histogram (ACCEPT / REVISE / OTHER) | 1,080 / 7 / 0 | 1,079 / 8 / 0 | 1,079 / 6 / 0 |
| Contacts-per-row histogram | 4: 13, 5: 1,060, 9: 7 | 4: 2, 5: 1,071, 8: 1, 9: 6 | 4: 3, 5: 1,072, 9: 5 |

The anchor's registered baseline of five executed revisions and two intent changes reproduces. B5e
executes seven revisions, the same count as cell B1, and all seven changed the intent (B1: 3 of 7).
Thirteen rows took four contacts rather than five, against the anchor's three and B1's two; the loop
is the anchor's throughout and is not ablated here, so these counts are recorded and not attributed.

**What could not be reproduced:** nothing in the M1 list. Cell B4b carries no `train-exemplars` store,
so it has no M1 supply record and no M1 diagnostic -- its trace was not streamed -- and the released
direct anchor runs no agent loop and has no Perception visit; both absences are structural, not
failures.

## The M4b slot-matching diagnostic

Computed with the official scorer's own matching, reconstructed from each arm's sealed outputs. Every
row's reconstruction was checked against that row's sealed official `slu_f1` word and character counts
before any table was built, and the per-type decomposition sums to each arm's official aggregate on
all four arms. **The A3 audit's anchor baseline reproduces exactly, and so does every one of cell
B4b's own first-pass readings** (date omissions 81 -> 77, time omissions 19 -> 13, time FN mass
-32.86, date FN mass -10.16, and the roster totals 302 exact / 369 omitted / 351 spurious /
750.76 surface mass), so the columns below are the same instrument the B4b verdict used.

| Type | Gold rows | Omits entirely (anchor / B4b / B1 / B5e) | Exact mentions | FN mass | FP mass |
| --- | ---: | ---: | ---: | ---: | ---: |
| date | 135 | 81 / 77 / 48 / **46** | 28 / 33 / 66 / **67** | 203.58 / 193.42 / 129.35 / **127.75** | 49.58 / 39.42 / 41.35 / 49.75 |
| time | 72 | 19 / 13 / 15 / **8** | 8 / 22 / 30 / **39** | 116.34 / 83.48 / 68.07 / **54.39** | 96.34 / 77.48 / 64.07 / **50.39** |
| media_type | 57 | 38 / 29 / 16 / 16 | 8 / 11 / 32 / 30 | 95.30 / 85.82 / 46.50 / 49.94 | 35.30 / 43.82 / 32.50 / 39.94 |
| transport_type | 36 | 25 / 24 / 16 / **14** | 10 / 11 / 18 / **20** | 51.75 / 49.75 / 35.50 / **31.50** | 5.75 / 3.75 / 9.50 / 7.50 |
| business_type | 29 | 22 / 22 / 14 / 14 | 2 / 3 / 12 / 12 | 49.47 / 48.02 / 31.12 / 31.12 | 19.47 / 20.02 / 19.12 / 17.12 |
| order_type | 22 | 19 / 16 / 15 / **18** | 1 / 3 / 5 / **2** | 44.12 / 39.99 / 34.95 / **41.13** | 18.12 / 21.99 / 6.95 / 9.13 |
| relation | 15 | 15 / 13 / 6 / **4** | 0 / 2 / 7 / **9** | 32.00 / 28.00 / 17.61 / **13.61** | 0.00 / 0.00 / 11.61 / 11.61 |
| event_name | 41 | 22 / 20 / 10 / 11 | 10 / 10 / 20 / 21 | 57.58 / 56.91 / 32.83 / 33.53 | 39.58 / 42.91 / 38.83 / 39.53 |

Roster totals, all types: gold mentions 941 (fixed); predicted mentions 910 / 923 / 1,000 / **986**;
exact mentions 272 / 302 / 470 / **480**; omitted mentions 393 / 369 / 266 / **252**; spurious
mentions 362 / 351 / 325 / **297**; filler-distance (surface) mass 814.46 / 750.76 / 534.14 /
**567.27**.

**This is where M4b's contribution inside the combination is visible, and it is real.** On the two
types the v2 cards were written for, B5e beats cell B1 on every reading: **time** omissions
15 -> 8, all-exact mentions 30 -> 39, FN mass 68.07 -> 54.39 (-13.68) and FP mass 64.07 -> 50.39
(-13.68); **date** omissions 48 -> 46, exact 66 -> 67, FN mass 129.35 -> 127.75. `relation` and
`transport_type` also improve. The combination omits the fewest mentions (252) and emits the fewest
spurious ones (297) of any arm on this base. Two types move the other way -- `order_type` (omissions
15 -> 18, exact 5 -> 2) and `media_type` (exact 32 -> 30) -- and the surface mass rises 534.14 ->
567.27 against B1, so the arm is slightly further from the corpus surface on the spans it does match.
**The mechanism did what it was built to do; it is simply too small at roster scale to push the
pooled CI95 lower bound above zero when it is measured on top of a leg that already gained
+12.61 pp.**

## Cost and duty cycle

| Figure | B5e | B1 | B4b | Anchor | Direct | Registered ceiling |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Generation contacts (per row) | **5,415 (5.014)** | 5,425 (5.023) | 5,407 (5.006) | 5,417 (5.016) | 1,080 (1.000) | 11,880 (11) |
| Repeated speech seconds | **15,453.99** | 15,494.60 | 15,432.81 | 15,459.76 | 3,084.53 | 33,930 |
| Prompt / completion tokens | **50,539,720 / 254,217** | 49,388,949 / 255,524 | 47,187,487 / 254,335 | 45,998,267 / 255,153 | 2,459,915 / 26,764 | -- |
| Native task-contract tool calls | **1,074** | 1,084 | 1,075 | 1,082 | 0 | 6,480 |
| FIT receipts / endpoints | **5,415 / 21,660** | 5,425 / 21,700 | 5,407 / 21,628 | -- | -- | -- / 47,520 |
| GPU hours (monitor active seconds) | **3.8709 (13,935.2 s)** | 3.6819 (13,255.0 s) | 3.4651 (12,474.3 s) | not in its receipts | 0.0871 (313.5 s) | 12.0 |
| Generation wall seconds | **14,482.9** | 13,894.2 | 12,796.8 | not in its receipts | 450.6 | -- |
| Slot occupancy; utilisation; parked | **0.851; 88.68 %; 0.037** | 0.877; 91.01 %; 0.045 | 0.925; 92.43 %; 0.025 | -- | 0.658; 55.66 %; 0.281 | -- |
| Mean latency (s); preprocess (s, workers) | **9.105; 14.26 at 8** | 8.982; 10.01 at 8 | 8.760; 13.68 at 8 | -- | 1.098; 13.03 at 8 | -- |
| Official scoring jobs (seconds) | **1 (326.66)** | 1 (166.22) | 1 (387.22) | -- | -- | 1 |

**Every figure the brief quoted from the flight receipts is confirmed**: 5,415 contacts,
15,453.99 repeated speech seconds, 50,539,720 prompt tokens, 254,217 completion tokens, 1,074 tool
calls, wall 14,482.9 s, occupancy 0.851, 3.871 GPU hours, utilisation 88.7 %, parked 0.037.

Every registered ceiling held with room: **45.6 %** of the contact ceiling, **45.5 %** of the speech
ceiling, **32.3 %** of the GPU-hour ceiling, **16.6 %** of the task-contract ceiling, and one official
scoring job of one. Both modules add prompt volume and not contacts, exactly as registered: against
the anchor **+4,541,453 prompt tokens (+9.87 %)** for two fewer contacts; against cell B1
**+1,150,771 (+2.33 %)**, which is M4b's slot-card increment measured on the wire; against cell B4b
+3,352,233 (+7.10 %), which is M1's. Completion tokens fall slightly on every comparison
(-936 against the anchor, -1,307 against B1).

FIT: `every_request_fits = true` on all **5,415** receipts (21,660 endpoints); minimum margin **6,043
tokens** in the `planner` phase against the 24,576-token slot. One honest note to record, exactly as
the B1 and B4b verdicts recorded theirs: the widest realised request needed **18,533 tokens**, which
is **550 tokens above the preregistration's section-9 registered static upper bound of 17,983** (the
anchor's widest realised role visit 15,382, plus the conservative static exemplar-supply bound 1,636,
plus M4b's largest measured per-role-visit increment 965). That is a 3.1 % overshoot of a bound the
package built as a *sum over different rows and different role visits*, and it leaves 6,043 tokens of
slot margin. B1's widest realised request was 15,976 and B4b's 16,334, so the combination's widest exceeds
both -- by 2,557 tokens over B1 and 2,199 over B4b: on at least one row the two increments land on
the same request, which the section-9 arithmetic allowed for but did not prove. **The FIT gate, not the
static bound, is the per-request authority** -- `core.preparation_fit.build_native_contact_fit_gate`
fits every realised immutable request against the resident tokenizer before it is transmitted -- and
it says every one of the 5,415 requests fit.

## What is not claimed

- **No superiority, generalization, paper-scale or held-out claim.** TRAIN Fold A is an exposed
  discovery roster; nothing is said about Fold B, DEV-1000 or the test split, which stay unread.
- **HARMFUL here does not mean "the combination hurt".** It means the registered non-inferiority
  bound was not met on an intent contrast whose point estimate is a one-row tie. The verdict applies
  the clause as written and says so; it does not claim a measured intent loss, and the per-scenario
  table shows no scenario losing intent beyond the band.
- **No claim that M4b is inert.** The slot decomposition shows its date and time mechanism working
  inside the combination; what this read establishes is only that its *pooled* increment on top of M1
  cannot be separated from zero at CI95 on 1,080 rows.
- **Module M4b's provisional obligation is not discharged and not revoked here.** That belongs to the
  B4b request-identical replicate, which was not sealed when this read ran.
- **No re-estimate of either module's own effect size.** The cell B1, B1-twin and B4b verdicts stand
  unchanged beside this one.
- **The additive decomposition is a point estimate.** "91.3 % M1, 18.5 % M4b, -9.8 % interaction" has
  no interval attached and must not be quoted as one; the interaction's own CI95 contains zero on
  every metric.
- **No component-causal attribution below the two stores.** Twenty exemplars arrive together and
  eight slot cards moved together; this cell cannot say which exemplar or which card paid.
- **Nothing about the review loop**, which is the anchor's here and is not ablated.
- **One pass.** Meeting the bar on this pass would not have been "replicated" and missing it is not
  "refuted"; greedy decoding at temperature 0 is not bitwise reproducible across batch compositions,
  so B5e and B1 trajectories differ row by row for reasons other than the slot store, and the paired
  bootstrap prices that variation without removing it.
- **A structural smoke result is never a quality result**, and the aborted first attempt's 25 contacts
  were never scored and never read.

## Exposure

**Zero model contacts; the sealed bytes were copied, never opened for writing.** This read made no
model, tokenizer, encoder, ASR or server contact and touched no serving session, flight worktree,
scheduled task or flight lock. The only scorer invocations are the model-free projection-v3 and TRAIN
symmetric scorings, five arms each, every one over a COPY of that arm's sealed `outputs.jsonl` written
under `SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-B5E-COMBINATION-PAIRED-ANALYSIS-V1/`. No sealed file was
opened for writing, moved or renamed; no exposure-ledger row, harness-admission receipt or results
ledger was edited by this read. Execution profile `model-free-check`.
