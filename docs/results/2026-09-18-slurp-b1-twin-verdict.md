# Cell B1 derangement twin: the retrieval key separated from the exemplars, module M1 on TRAIN A

Status: **ADMITTED. Owner decision 18 branch A.** The pooled official SLU delta of
(B1 arm minus the derangement twin) is **+7.83 pp with a CI95 lower bound of +5.85 pp above zero**,
so clause 1b of the preregistered rule passes, every other clause that the arm read already passed
still passes, and module M1 is admitted **as speech-keyed exemplar supply** -- not merely as
exemplar presence. The twin is not inert: it beats the sealed anchor by **+4.77 pp**
[+3.20, +6.36], so twenty *unrelated* real annotated exemplars buy 37.8 % of the arm's +12.61 pp
official gain and the row's own speech key buys the remaining 62.2 %. On intent the split is far
sharper: the twin is nil (+0.19 pp, CI95 [-1.03, +1.39]) and the key carries +2.04 pp of the arm's
+2.22 pp. Root: the B1 twin paired-read agent, 2026-09-18. Program:
`docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md` (module M1, cell B1).
Preregistration: `docs/readiness/2026-09-17-slurp-b1-exemplars-k20-anchor-v2-preregistration.md`
(section 4 the twin, sections 5-7 fixed before contact), with
`docs/readiness/2026-09-17-slurp-b1-exemplars-k20-anchor-v2-recovery-v1.md` and its
`analysis-recipe-v1.json`. Contingency: owner decision 18 of 2026-09-18
(`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`), taken after the twin sealed
and **before** this read. Margins: the TRAIN A own null of cell B0r, **h_SLU = 1.1218 pp** and
**h_intent = 1.0051 pp** at CI95 (`docs/results/2026-09-17-slurp-b0-review-off-redecision-v2.md`).

## What flew

One attempt, FINALIZED on the first pass. Run
`SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TWIN-TRAIN-FOLD-A-V2`, attempt
`attempt-slurp-native-exemplars-k20-anchor-twin-train-fold-a-generation-v2`, manifest
**COMPLETED** at study commit `a7ce8f4c0447f91c62f56c536dbee3f99b48eeac`, composed config
`25daa5afb334a899091c6481a9febb33660743bfe96286c8d89903339b788d5c`, protocol
`4abd62bb6da4888095b57c843e59bb045a74bfb6fcce6b73ae3a4435f9207b2c` -- both equal to the values the
preregistration's section 2 registers -- arm `speech-feature-query-native-tools`, profile
`bounded-discovery-probe`, split identity
`61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, role `discovery`,
one official complete scoring job, created 2026-09-18T00:26:32Z. It flew on the E3c-fixed code and
took the REVISE route on nine rows, every one of which the pre-fix tree would have aborted on.

The one factor against the cell B1 arm is the **retrieval key**: every row receives another Fold A
recording's sealed full-utterance speech vector, drawn by the seeded within-delivered-scenario
derangement (`scripts/build_slurp_exemplar_twin_vectors.py`, seed 20260917; vectors
`92e7f72e5566aa8dad2ed75b8ddc3df58dd107ef2de57dc0e1aab66e2ad616c5`). Store, release, snapshot,
k = 20, fuse policy, rank policy, rendering, role graph, instruction templates, roster, session and
contact ceiling are the arm's.

### Provenance

| Artifact | SHA-256 |
| --- | --- |
| twin `scores.json` | `7e8b995e216499ebdf2377a045fcd951be4df0990ea68a3e70681a04db3e2d91` |
| twin `run-manifest.json` | `ee83cc68030a885ad33530148fd95f1f82e7067dee2b3ab974723c6877529e2f` |
| twin `outputs.jsonl` | `a03825ad871daafcc1b00a905898f15fa371ab57d413456bd364e5067fd3e380` |
| twin `trace.jsonl` | `53bdc011154e6a263457f144b831e43566487588311db461e40d9b712210d906` |
| twin `flight-receipts.json` | `3218afdac9f8b5c683788dc43b72c07294299ff972f73d4100510e1d5d9d0407` (declared `receipts_hash` `563a51d11ddf99d2f0950e8bad1723705b51c4b4d0490494dd81d75c793de34f`) |
| B1 arm `scores.json` | `a7105b328509a8bd00c4678fd076e9be4d242b6189bb82bbd290bd596e3c9078` |
| B1 arm `run-manifest.json` | `b07ed553ff9f78b8e3ead6797bb66fb92a1820793b8aa5061576c6f66aa1a8ad` |
| B1 arm `outputs.jsonl` | `db9cd6329b0837d8f120f153556c951a68969da167d245d695eb35916237deca` |
| B1 arm `trace.jsonl` | `874a91a8ef1729289cde6c3164d9a834bbe702cda9075a6e84155b5b688aba8a` |
| anchor `scores.json` | `7360876322488e5fda689fcafda00e90da2ebf559e5a35e635c550f940202b47` |
| anchor `outputs.jsonl` | `d87d71e8fa0fe93b45d5c6817ba125b016d8d91f44a14309171dd0f3a64270d8` |
| anchor `trace.jsonl` | `912e9853e2e32afec9a009afd0aecdae696f6299343f22d3613f4edcde2c6e67` |
| direct anchor `scores.json` | `7840a959fe4f43928fda0e0cacfe8c0ee4200116bfcd269bfe3451b59da29c38` |
| direct anchor `outputs.jsonl` | `5c182ddfc81effe2465fb58f052842538f22ead3601355dbe77427c937decd61` |
| roster `docs/receipts/rosters/slurp-evo-fold-a-v2.json` | `1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d` |
| roster metadata | `07f4cd83b83d83d65500a328e0a38421ede575195c63ae118def0d1006c14e34` |
| parent speech key vectors | `d0f06ed21c6a576d8118d5a914e34807c24a3d3523d89e7b30d90575d24104ff` |
| deranged speech key vectors | `92e7f72e5566aa8dad2ed75b8ddc3df58dd107ef2de57dc0e1aab66e2ad616c5` |
| registered derangement proof | `84929b56a04aa579e4e840f222b1520fd5cf36613f84292f3b9331921d02c39d` |
| exemplar release (pinned) | `171aa4a82c2b15fff2c72e907ea80298be8d72309cca0d7367eb50debb042129` |
| exemplar snapshot: declared content hash / file bytes | `4c498dc0282055b9fe036ed7e950af519bd48b5f26e76876d0250727196a72e9` / `fcb5506c63653abe996dea15fdccd7c81a84a837b6377ca13f5b35d73283d6b2` |
| paired read `analysis/SAEA-SLURP-B1-TWIN-PAIRED-ANALYSIS-V1/score-contrasts.json` | `37cec40d539df80eb02e9b45f8965669105f2a91588dafbf0d921aa526d02d1a` |
| paired read `.../README.md` | `c8012142a3c5fd0e8fdb1550b47b454805fd14f4c9eb17d70f6a1b8817912631` |
| paired read driver `.../b1_twin_paired_read.py` | `f8b14341bfaa3bfaca701c86d7e1cd06cdfa395483141a8aa0b407c153fef932` |
| paired read `.../per-scenario-tables.json` | `a04f37994f1c4a7cae41deb49157abf9b8e0e48940334c54de3679d8a504f3d0` |
| paired read `.../m1-diagnostics.json` | `5993fb4110c3a976ea82b750aa41b3df2e469421469d7e61ddf5c75e0c65a5db` |
| paired read `.../twin-integrity.json` | `98827540a505301459581ee88f2730947072a495fa6cad08f895f334b38ae01f` |

Every hash above was recomputed from the file before it was read. The driver is an adapted copy of
the cell B1 arm read's own driver
(`analysis/SAEA-SLURP-B1-EXEMPLARS-K20-PAIRED-ANALYSIS-V1/b1_paired_read.py`, sha256
`2644710aee90b62fa200aed847ddfda2544e776f4f59c57853e4fc7dd4479225`); only the arm list, the
contrast list, the decision block and the diagnostics assembly change, and every estimator call --
`analysis.null_calibration_cli.rows_for`, `analysis.null_calibration.pooled_f1`,
`analysis.paired.resampled_statistic`, `analysis.paired.paired_contrast` -- is unchanged. Paired
whole-speaker cluster bootstrap, 10,000 draws, seed 20260915, CI95 for advancement and CI90 for
diagnostics as percentiles of the same retained replicate sequence; sensitivity the paired
scenario-stratified row bootstrap on the same draws and seed. Rows: 1,080 scored per arm; parsed
1,076 twin, 1,076 B1 arm, 1,073 anchor, 1,080 direct.

## The STOP condition, closed before any twin table was read

The three registered aggregates and, additionally, the **cell B1 arm verdict's own
`B1 minus anchor` table** were recomputed from the sealed bytes and required to agree to the
hundredth of a point before the twin contrasts were opened. **PASSED**, with zero failures over
seven metric rows (left value, right value, delta, both CI95 bounds, and for the per-row metrics
saves, harms and ties):

| Metric | Verdict | Recomputed | Verdict CI95 | Recomputed CI95 |
| --- | ---: | ---: | --- | --- |
| Official pooled SLU-F1 | 48.53 -> 61.14, +12.61 | 48.5336 -> 61.1394, +12.6058 | [+10.54, +14.60] | [+10.5381, +14.5983] |
| Intent | 77.96 -> 80.19, +2.22 | 77.9630 -> 80.1852, +2.2222 | [+0.74, +3.71] | [+0.7407, +3.7073] |
| Scenario | 84.81 -> 86.39, +1.57 | 84.8148 -> 86.3889, +1.5741 | [+0.57, +2.53] | [+0.5671, +2.5316] |
| Action | 79.26 -> 81.39, +2.13 | 79.2593 -> 81.3889, +2.1296 | [+0.64, +3.56] | [+0.6421, +3.5606] |
| Pooled span F1 | 29.50 -> 48.43, +18.93 | 29.4976 -> 48.4286, +18.9311 | [+15.93, +21.76] | [+15.9278, +21.7648] |
| Exact slot F1 (row mean) | 19.02 -> 31.35, +12.33 | 19.0202 -> 31.3480, +12.3278 | [+10.38, +14.36] | [+10.3819, +14.3644] |
| SLU-F1 (row mean) | 30.29 -> 40.15, +9.85 | 30.2903 -> 40.1451, +9.8548 | [+8.19, +11.55] | [+8.1913, +11.5464] |

Saves / harms / ties reproduce exactly (intent 43 / 19 / 1,018; scenario 28 / 11 / 1,041; action
42 / 19 / 1,019; exact slot F1 213 / 38 / 829; row SLU-F1 276 / 63 / 741), as do the registered
anchor (48.53 / 77.96 / 84.81 / 79.26 / 29.50), direct (33.89 / 73.70 / 82.69 / 75.09 / 21.10) and
arm aggregates under projection v3 (51.99 / 79.35 and 34.31 / 75.37 and 62.67 / 81.76) and under
the TRAIN symmetric scorer (52.09 / 41.38, 34.46 / 24.38, 62.97 / 54.51). The arm's symmetric
`B1 minus anchor` pooled SLU delta recomputes as **+10.8854**, the registered value.

## B1 arm minus the derangement twin -- clause 1b, primary for this read (percentage points)

| Metric | Twin | B1 arm | Delta | Speaker CI95 | Speaker CI90 | Scenario-stratified CI90 | Equal-scenario |
| --- | ---: | ---: | ---: | --- | --- | --- | ---: |
| Official pooled SLU-F1 | 53.30 | 61.14 | **+7.83** | [+5.85, +9.75] | [+6.17, +9.42] | [+6.19, +9.53] | +7.53 |
| Intent (scenario+action) | 78.15 | 80.19 | **+2.04** | [+0.49, +3.78] | [+0.73, +3.47] | [+0.83, +3.24] | +2.04 |
| Scenario | 85.65 | 86.39 | +0.74 | [-0.32, +1.83] | [-0.17, +1.64] | [-0.19, +1.67] | +0.74 |
| Action | 79.35 | 81.39 | +2.04 | [+0.52, +3.70] | [+0.74, +3.42] | [+0.83, +3.24] | +2.04 |
| Pooled span F1 | 36.88 | 48.43 | **+11.55** | [+8.94, +14.07] | [+9.35, +13.66] | [+9.17, +13.93] | +11.09 |
| Exact slot F1 (row mean) | 23.01 | 31.35 | **+8.34** | [+6.64, +10.03] | [+6.90, +9.77] | [+6.74, +10.00] | +8.34 |
| SLU-F1 (row mean) | 33.33 | 40.15 | **+6.82** | [+5.29, +8.30] | [+5.52, +8.08] | [+5.52, +8.14] | +6.82 |

Saves / harms / ties with the exact two-sided McNemar p: intent 43 / 21 / 1,016 (**8.15e-3**);
scenario 22 / 14 / 1,044 (2.43e-1); action 43 / 21 / 1,016 (**8.15e-3**); exact slot F1
159 / 42 / 879 (**3.22e-17**); row SLU-F1 207 / 70 / 803 (**6.87e-17**). Six of the seven intervals
exclude zero; only **scenario accuracy** does not (+0.74, CI95 [-0.32, +1.83], sign test p = 0.24),
which is the one metric on which the presence of twenty in-scenario exemplars and the row's own key
are nearly interchangeable. The scenario-stratified sensitivity agrees on every row.

## The twin minus the sealed anchor -- what twenty unrelated exemplars alone do

| Metric | Anchor | Twin | Delta | Speaker CI95 | Speaker CI90 | Scenario-stratified CI90 | Equal-scenario |
| --- | ---: | ---: | ---: | --- | --- | --- | ---: |
| Official pooled SLU-F1 | 48.53 | 53.30 | **+4.77** | [+3.20, +6.36] | [+3.46, +6.10] | [+3.19, +6.36] | +4.60 |
| Intent (scenario+action) | 77.96 | 78.15 | +0.19 | [-1.03, +1.39] | [-0.84, +1.19] | [-0.83, +1.20] | +0.19 |
| Scenario | 84.81 | 85.65 | +0.83 | [-0.10, +1.77] | [+0.00, +1.62] | [+0.00, +1.76] | +0.83 |
| Action | 79.26 | 79.35 | +0.09 | [-1.17, +1.31] | [-0.97, +1.10] | [-0.93, +1.11] | +0.09 |
| Pooled span F1 | 29.50 | 36.88 | **+7.38** | [+5.01, +9.67] | [+5.40, +9.28] | [+5.23, +9.56] | +6.93 |
| Exact slot F1 (row mean) | 19.02 | 23.01 | **+3.99** | [+2.42, +5.52] | [+2.70, +5.25] | [+2.56, +5.43] | +3.99 |
| SLU-F1 (row mean) | 30.29 | 33.33 | **+3.04** | [+1.74, +4.31] | [+1.95, +4.12] | [+1.83, +4.26] | +3.04 |

Saves / harms / ties: intent 23 / 21 / 1,036 (p = 8.80e-1); scenario 21 / 12 / 1,047 (1.63e-1);
action 23 / 22 / 1,035 (1.00e+0); exact slot F1 112 / 50 / 918 (**1.24e-6**); row SLU-F1
159 / 81 / 840 (**5.36e-7**). **The twin's whole effect is on entities and none of it is on
labels.** Its intent, scenario and action intervals all contain zero and sit inside the own null;
its span and slot intervals are bounded well away from zero.

### The additive decomposition

The contrasts are exactly additive on every metric (the twin arm is a genuine intermediate):

| Metric | arm minus anchor | = twin minus anchor | + arm minus twin | presence share |
| --- | ---: | ---: | ---: | ---: |
| Official pooled SLU-F1 | +12.6058 | +4.7708 | +7.8349 | 37.8 % |
| Intent | +2.2222 | +0.1852 | +2.0370 | 8.3 % |
| Scenario | +1.5741 | +0.8333 | +0.7407 | 52.9 % |
| Action | +2.1296 | +0.0926 | +2.0370 | 4.3 % |
| Pooled span F1 | +18.9311 | +7.3788 | +11.5523 | 39.0 % |
| Exact slot F1 (row mean) | +12.3278 | +3.9857 | +8.3421 | 32.3 % |
| SLU-F1 (row mean) | +9.8548 | +3.0366 | +6.8183 | 30.8 % |

"Presence share" is the fraction of the arm's own gain the token-matched, wrongly-keyed exemplars
already deliver. It is a point-estimate decomposition, not an interval statement.

## The twin minus the released direct anchor (secondary, never a gate)

Pooled SLU **+19.42** [+16.31, +22.58]; intent +4.44 [+2.12, +6.69]; scenario +2.96
[+0.76, +5.28]; action +4.26 [+1.90, +6.63]; pooled span F1 +15.78 [+12.02, +19.52]; exact slot F1
row mean +12.29 [+10.10, +14.60]; row SLU-F1 +17.27 [+15.10, +19.62]. Saves / harms: intent
120 / 72 (p = 6.55e-4), row SLU-F1 334 / 63 (p = 1.12e-45). One honest note, exactly as the arm's
secondary contrast carried: against the **direct** anchor the scenario `alarm` loses intent beyond
the band (-6.67, CI95 [-15.00, -1.37], net harmed 4 rows) and owner decision 17's diagnostic flags
`general` (net harmed +6) and `lists` (+5). The band is a clause of the rule only against the
**sealed anchor**, where nothing breaches on any gating contrast; against the direct anchor it is
reported, not gating.

## The rule, applied unchanged

| Clause | Requirement | Value | Threshold | Passes |
| --- | --- | ---: | ---: | --- |
| 1, pooled SLU gain vs the anchor | CI95 lower bound of (B1 - anchor) > 0 | +10.5381 | 0 | **YES** |
| 1b, pooled SLU gain vs the twin | CI95 lower bound of (B1 - twin) > 0 | **+5.8503** | 0 | **YES** |
| 2, intent non-inferiority vs the anchor | CI95 lower bound > -1.0051 | +0.7407 | -1.0051 | **YES** |
| 2 (reported) intent non-inferiority vs the twin | CI95 lower bound > -1.0051 | +0.4921 | -1.0051 | **YES** |
| 3, normalised-scorer agreement vs the anchor | symmetric delta agrees in sign | +10.8854 vs +12.6058 | same sign | **YES** |
| 3 (reported) vs the twin | symmetric delta agrees in sign | +7.0695 vs +7.8349 | same sign | **YES** |
| 4, scenario band vs the anchor | no scenario's paired intent CI95 upper bound below zero | 0 of 18 breaching | CI95 upper < 0 | **YES** |
| 4 (reported) vs the twin | as above | 0 of 18 breaching | CI95 upper < 0 | **YES** |

None of the three HARMFUL triggers fires on any gating contrast. Owner decision 17's diagnostic
fires on **no scenario** for `B1 minus anchor`, for `B1 minus twin` or for `twin minus anchor`.

**Owner decision 18, branch reached: A.** "(B1 minus twin) has a positive CI95 lower bound, so M1
is ADMITTED as speech-keyed exemplar supply under the registered rule." Branch B (the twin ties the
arm while beating the anchor, which would have registered the twin's bytes as module
**M1p: delivered-scenario annotated-exemplar presence**) is **not** reached: the arm beats the twin
with a CI95 lower bound of +5.85 pp. The twin's own +4.77 pp over the anchor is recorded here as a
measured fact about exemplar *presence*, and it is **not** registered as a module by this read --
decision 18 makes that registration conditional on branch B, which did not occur. Read once, from
the single official score of the complete manifest; no repeat, no re-score, no row filtering.

## Every scenario, B1 arm minus twin (natural mixture; equal-scenario mean in the last row)

| Scenario | n | Twin SLU | B1 SLU | Delta | Twin intent | B1 intent | Delta | Intent CI95 | Net harmed | Flag | Beyond band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | --- |
| alarm | 60 | 58.30 | 65.28 | +6.98 | 85.00 | 81.67 | -3.33 | [-10.59, +6.35] | +2 | no | no |
| audio | 60 | 52.09 | 60.35 | +8.26 | 80.00 | 78.33 | -1.67 | [-7.14, +5.13] | +1 | no | no |
| calendar | 60 | 52.20 | 64.16 | +11.96 | 75.00 | 78.33 | +3.33 | [-3.23, +10.34] | -2 | no | no |
| cooking | 60 | 65.69 | 64.74 | **-0.95** | 88.33 | 88.33 | 0.00 | [-4.62, +4.84] | 0 | no | no |
| datetime | 60 | 63.37 | 69.80 | +6.43 | 85.00 | 88.33 | +3.33 | [+0.00, +8.62] | -2 | no | no |
| email | 60 | 51.52 | 57.93 | +6.41 | 88.33 | 83.33 | -5.00 | [-10.34, +0.00] | +3 | no | no |
| general | 60 | 20.02 | 20.41 | +0.39 | 36.67 | 43.33 | +6.67 | [+0.00, +13.85] | -4 | no | no |
| iot | 60 | 59.70 | 64.30 | +4.60 | 86.67 | 88.33 | +1.67 | [+0.00, +5.08] | -1 | no | no |
| lists | 60 | 44.67 | 53.45 | +8.77 | 81.67 | 85.00 | +3.33 | [+0.00, +8.93] | -2 | no | no |
| music | 60 | 37.22 | 48.87 | +11.65 | 76.67 | 78.33 | +1.67 | [-3.77, +7.41] | -1 | no | no |
| news | 60 | 52.02 | 60.85 | +8.84 | 80.00 | 83.33 | +3.33 | [+0.00, +9.09] | -2 | no | no |
| play | 60 | 46.88 | 49.94 | +3.05 | 51.67 | 60.00 | **+8.33** | [-1.61, +17.46] | -5 | no | no |
| qa | 60 | 58.08 | 58.16 | +0.08 | 71.67 | 75.00 | +3.33 | [+0.00, +8.33] | -2 | no | no |
| recommendation | 60 | 50.59 | 68.67 | **+18.08** | 91.67 | 90.00 | -1.67 | [-9.09, +5.36] | +1 | no | no |
| social | 60 | 47.07 | 57.33 | +10.26 | 66.67 | 75.00 | **+8.33** | [+1.79, +15.62] | -5 | no | no |
| takeaway | 60 | 54.50 | 60.43 | +5.93 | 83.33 | 85.00 | +1.67 | [+0.00, +5.08] | -1 | no | no |
| transport | 60 | 54.27 | 62.79 | +8.52 | 86.67 | 90.00 | +3.33 | [+0.00, +7.35] | -2 | no | no |
| weather | 60 | 57.68 | 73.93 | **+16.25** | 91.67 | 91.67 | 0.00 | [+0.00, +0.00] | 0 | no | no |
| **equal-scenario mean** | 18 | | | **+7.53** | | | **+2.04** | | | | |

Seventeen of eighteen scenarios gain on pooled SLU; only `cooking` loses, by 0.95 pp. The extremes
are `recommendation` +18.08, `weather` +16.25 and `calendar` +11.96 at the top and `cooking`
-0.95, `qa` +0.08 and `general` +0.39 at the bottom -- the same two scenarios (`qa`, `cooking`) that
moved least against the anchor, and here they show that on those two the key adds nothing over
presence. No scenario loses intent beyond the band and no scenario reaches owner decision 17's
five-row flag; the worst net figure is +3 (`email`).

## Every scenario, twin minus the sealed anchor

| Scenario | n | Anchor SLU | Twin SLU | Delta | Anchor intent | Twin intent | Delta | Intent CI95 | Net harmed | Flag | Beyond band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | --- |
| alarm | 60 | 52.66 | 58.30 | +5.64 | 83.33 | 85.00 | +1.67 | [-4.76, +11.32] | -1 | no | no |
| audio | 60 | 47.75 | 52.09 | +4.33 | 76.67 | 80.00 | +3.33 | [-5.13, +8.93] | -2 | no | no |
| calendar | 60 | 48.38 | 52.20 | +3.82 | 75.00 | 75.00 | 0.00 | [+0.00, +0.00] | 0 | no | no |
| cooking | 60 | 62.47 | 65.69 | +3.22 | 85.00 | 88.33 | +3.33 | [-3.17, +9.84] | -2 | no | no |
| datetime | 60 | 59.52 | 63.37 | +3.86 | 83.33 | 85.00 | +1.67 | [+0.00, +5.00] | -1 | no | no |
| email | 60 | 36.64 | 51.52 | **+14.88** | 85.00 | 88.33 | +3.33 | [+0.00, +8.47] | -2 | no | no |
| general | 60 | 15.45 | 20.02 | +4.57 | 36.67 | 36.67 | 0.00 | [-6.78, +6.35] | 0 | no | no |
| iot | 60 | 55.53 | 59.70 | +4.17 | 86.67 | 86.67 | 0.00 | [-4.76, +5.00] | 0 | no | no |
| lists | 60 | 43.55 | 44.67 | +1.12 | 83.33 | 81.67 | -1.67 | [-5.66, +0.00] | +1 | no | no |
| music | 60 | 34.53 | 37.22 | +2.69 | 76.67 | 76.67 | 0.00 | [-4.69, +4.84] | 0 | no | no |
| news | 60 | 44.24 | 52.02 | +7.78 | 80.00 | 80.00 | 0.00 | [+0.00, +0.00] | 0 | no | no |
| play | 60 | 46.82 | 46.88 | +0.06 | 58.33 | 51.67 | **-6.67** | [-16.22, +3.39] | +4 | no | no |
| qa | 60 | 57.04 | 58.08 | +1.04 | 75.00 | 71.67 | -3.33 | [-8.33, +0.00] | +2 | no | no |
| recommendation | 60 | 49.75 | 50.59 | +0.84 | 90.00 | 91.67 | +1.67 | [-3.64, +7.55] | -1 | no | no |
| social | 60 | 34.74 | 47.07 | **+12.33** | 66.67 | 66.67 | 0.00 | [+0.00, +0.00] | 0 | no | no |
| takeaway | 60 | 48.84 | 54.50 | +5.66 | 85.00 | 83.33 | -1.67 | [-5.08, +0.00] | +1 | no | no |
| transport | 60 | 51.34 | 54.27 | +2.93 | 86.67 | 86.67 | 0.00 | [+0.00, +0.00] | 0 | no | no |
| weather | 60 | 53.81 | 57.68 | +3.87 | 90.00 | 91.67 | +1.67 | [+0.00, +5.66] | -1 | no | no |
| **equal-scenario mean** | 18 | | | **+4.60** | | | **+0.19** | | | | |

All eighteen scenarios gain on pooled SLU, none loses, and the gain concentrates where the anchor
was weakest on entities (`email` +14.88, `social` +12.33). No scenario loses intent beyond the band
and none reaches the decision-17 flag; `play` is the worst intent stratum (-6.67, net harmed +4) and
its interval contains zero.

## Projection v3 and the TRAIN symmetric view, beside the rule

Owner decision 7 makes `slurp-slu-official-projected-v3-train` the fixed post-processing of every
official number; owner decision 14 registered the TRAIN sibling
`slurp-slu-f1-normalized-v1-train`. Neither is a clause of the rule. Each arm's sealed
`outputs.jsonl` was COPIED under the analysis directory and the registered scorers read the copy.
The anchor's, the direct anchor's and the B1 arm's readings reproduce the cell B1 verdict exactly,
which is what licenses reading the twin's numbers beside them.

| Arm | v3 SLU | v3 intent | v3 scenario | v3 action | v3 span F1 | Labels / fillers changed |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| anchor | 51.99 | 79.35 | 85.46 | 80.65 | 40.30 | 20 / 195 |
| **twin** | **55.76** | **80.09** | **86.39** | **81.30** | **44.25** | 29 / **125** |
| B1 arm | 62.67 | 81.76 | 87.13 | 82.96 | 52.65 | 24 / 90 |
| direct | 34.31 | 75.37 | 84.17 | 75.93 | 23.24 | 47 / 36 |

v3 contrasts: **B1 - twin SLU +6.90 [+4.83, +8.92]**, intent +1.67 [+0.19, +3.29], span F1 +8.40
[+5.77, +10.94]; **twin - anchor SLU +3.77 [+2.08, +5.45]**, intent +0.74 [-0.26, +1.66], span F1
+3.95 [+1.79, +6.04]; twin - direct SLU +21.45 [+18.32, +24.62]. For reference the arm's own
`B1 - anchor` v3 delta reproduces at +10.67 [+8.55, +12.77]. The filler-normalisation counts order
themselves exactly as the entity story predicts -- anchor 195, twin 125, B1 arm 90 -- so the
wrongly-keyed exemplars already move the surface forms about half of the way the correctly-keyed
ones do.

| Arm | Official pooled SLU | Symmetric pooled SLU | Delta | Official span F1 | Symmetric span F1 | False merges |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| anchor | 48.53 | 52.09 | +3.56 | 29.50 | 41.38 | 34 |
| **twin** | **53.30** | **55.90** | **+2.60** | **36.88** | **46.10** | 34 |
| B1 arm | 61.14 | 62.97 | +1.83 | 48.43 | 54.51 | 34 |
| direct | 33.89 | 34.46 | +0.57 | 21.10 | 24.38 | 34 |

Symmetric contrasts: **B1 - twin SLU +7.07 [+4.94, +9.16]**, intent +2.04 [+0.49, +3.78], span F1
+8.41 [+5.71, +10.98]; **twin - anchor SLU +3.82 [+2.12, +5.51]**, intent +0.19 [-1.03, +1.39],
span F1 +4.71 [+2.33, +7.12]; the arm's `B1 - anchor` reproduces at +10.89 [+8.72, +13.00]. Every
gating sign agrees with the unprojected view. The symmetric-repair column falls monotonically
(anchor +3.56, twin +2.60, arm +1.83): representation alignment is bought partly by presence and
partly by the key, and **+7.07 of the arm's +7.83 advantage over the twin survives symmetric
normalisation**, so the key's contribution is not a surface-form artifact.

The devel-bound `slurp-slu-f1-normalized-v1` still refuses this roster, reproduced here verbatim:
`SlurpOfficialEvalError: outputs sample_id 'slurp:train:000007:audio--1504197557' is not part of
SLURP split 'devel'`.

## The mandatory M1 diagnostics, twin beside arm

The instrument is each arm's own sealed trace -- the first-Perception response projected through
`rails.slurp_intent_hypotheses.project_bounded_slurp_intent_hypotheses`, the flight's own recorded
`train-exemplars` value ids, and each arm's sealed delivered answer -- exactly the instrument the
cell B1 verdict used. **It reproduces every one of that verdict's arm and anchor readings.**

| Diagnostic | Twin | B1 arm | Anchor |
| --- | ---: | ---: | ---: |
| Supplied exemplars per row | 20 on 1,080 / 1,080; **4,983** distinct values of 9,354 | 20 on 1,080 / 1,080; 4,990 distinct | -- |
| Gold intent among the arm's own Perception candidates | 939 (0.8694) | 939 (0.8694) | 937 (0.8676) |
| Delivered intent among the arm's own candidates | 1,043 (0.9657) | 1,044 (0.9667) | 1,051 (0.9731) |
| Delivered intent correct | 844 (0.7815) | 866 (0.8019) | 842 (0.7796) |
| **Solver escape to a neighbour intent** | **3 rows (0.28 %)**, 1 onto gold | 6 rows (0.56 %), 5 onto gold | -- |
| Delivered intent outside candidates and exemplars | 34 | 30 | -- |
| Delivered intent present among the twenty exemplar intents | **630** | 979 | -- |
| A2 recovery set available through this arm's own exemplars | **40 rows** | 113 rows | -- |
| ... delivered correctly | **2 of 40** | 10 of 113 | 0 of the arm's 113; 0 of the twin's 40 |
| Candidate-union coverage realised (anchor candidates union exemplar intents) | **0.9046** | 0.9722 (A2's number) | 0.8676 candidates only |
| Intent echo (neighbour plurality equals the delivered intent) | **0.3778** | 0.7241 (A2: 0.729) | -- |
| Gold filler recall among the twenty | **0.1966** (185 / 941) | 0.5770 (543 / 941; A2: 0.566) | -- |
| Gold type recall among the twenty | **0.6962** | 0.9590 (A2: 0.960) | -- |
| Delivered mentions echoing a supplied exemplar filler | **175 of 903 (0.194)** | 500 of 1,000 (0.500) | 89 of 910 (0.098) against the twin's supply; 265 of 910 (0.291) against the arm's |
| Gold-exact mentions | 382 | 501 | 340 |

**Candidate-union coverage collapses from 0.9722 to 0.9046 under the derangement, and the coverage
lever all but disappears**: the A2 recovery set -- rows whose gold intent the anchor's own
candidates miss but the twenty neighbours carry -- shrinks from 113 rows to 40, and the twin
converts 2 of them against the arm's 10. The escape-to-neighbour-intent rate halves, 0.56 % to
0.28 %. That is the *label* channel, and it is exactly where the twin's intent delta is nil.

**The entity channel survives the derangement at about a third strength.** The twin's own filler
echo is 0.194 against a base rate of 0.098 (the anchor's answers matched against the same deranged
supply) -- a doubling -- while the arm's is 0.500 against its own base rate of 0.291, a 1.7x. Gold
filler recall among the supplied twenty falls from 0.577 to 0.197 and gold-exact mentions land at
382, between the anchor's 340 and the arm's 501. In one sentence: the wrongly-keyed exemplars still
teach the *form* of a SLURP answer, and only the right key supplies its *content*.

Rendered exemplar volume, per row, from the pinned snapshot content the flight's own supply record
names: twin mean **1,874.9** characters, p50 1,807, p95 2,696, max **3,232** -- against the arm's
1,874.4 / 1,807 / 2,696 / 3,232. The two distributions are effectively identical, which is the
token-matching the preregistration claimed by construction, now measured. Both are inside the
preregistration's section-9 rendered-block maximum of 4,332 characters (1,083 proxy tokens).

Review loop, and the E3c path in flight:

| Quantity | Twin | B1 arm | Anchor |
| --- | ---: | ---: | ---: |
| Rows with a Planner REVISE token | **9** | 7 | 5 |
| Rows with a second Solver visit (revisions executed) | **9** | 7 | 5 |
| Rows whose intent changed across the revision | **7** | 3 | 2 |
| Exemplar acquire transitions per row | exactly 1 on 1,080 / 1,080 | exactly 1 on 1,080 / 1,080 | n/a |
| Contacts-per-row histogram | 4: 7, 5: 1,064, 9: 9 | 4: 2, 5: 1,071, 8: 1, 9: 6 | 4: 3, 5: 1,072, 9: 5 |

The anchor's registered baseline of five executed revisions and two intent changes reproduces. The
twin executes nine revisions -- every one a row the pre-fix tree would have aborted on -- and the
acquire-transition histogram is again exactly 1 on 1,080 of 1,080 rows, so the E3c fix behaved on
this flight as it did on the arm's.

## Twin integrity

What the sealed supply receipts actually carry: `supply_bootstrap_value_ids`,
`supply_bootstrap_facet_ids`, `supply_acquired_value_ids_by_transition`,
`supply_acquired_facet_ids_by_transition`, `supply_final_visible_value_ids` and
`supply_final_visible_facet_ids`.

- **Facet ids are not available to compare.** The exemplar supply is value-only: on **every row of
  both arms** `supply_final_visible_facet_ids` is the empty list, and no `train-exemplars` facet id
  appears anywhere in either flight's supply records. The brief's "share of rows whose supplied
  exemplar facet ids differ from the arm's" is therefore not computable as stated; what is
  computable, and reported below, is the same comparison over the **value** ids the receipts do
  carry.
- **Supplied value-id sets differ on 1,080 of 1,080 rows (100.0 %).** Mean overlap **2.34** of 20,
  median **0**, minimum 0, maximum 18; **571 rows share no value at all** with the arm's twenty.
  Overlap histogram: 0 -> 571 rows, 1 -> 93, 2 -> 94, 3 -> 48, 4 -> 46, 5 -> 37, 6 -> 38, 7 -> 35,
  8 -> 23, 9 -> 22, 10 -> 16, 11 -> 20, 12 -> 13, 13 -> 10, 14 -> 7, 15 -> 3, 16 -> 2, 17 -> 1,
  18 -> 1. No row received an identical set.
- **Supply scenario.** The plurality scenario of the twenty supplied exemplar intents equals the
  **sealed anchor's delivered scenario** -- the derangement's own bucket key -- on **874 of 1,080**
  twin rows (80.9 %), statistically indistinguishable from the arm's **873 of 1,080** (80.8 %). It
  equals the row's *own* delivered scenario on 855 twin rows (79.2 %) against the arm's 889
  (82.3 %), and the roster's recorded scenario on **758 twin rows (70.2 %)** against the arm's
  **903 (83.6 %)**. Twin and arm share the plurality supply scenario on 742 rows (68.7 %). So the
  twin is supplied with exemplars of the right *kind* at the same rate and of the right *row* far
  less often -- which is precisely the control the registration intended.
- **The derangement map, recomputed from the two sealed vector files alone.** Each twin row's key
  vector was matched byte-for-byte (SHA-256 of the serialised content vector) against the parent
  vector file: **1,080 of 1,080 rows resolve to exactly one parent row**, **0 fixed points**,
  **1,079 distinct sources** (one source delivered twice, one unused) -- the registered proof's own
  figures. **1,080 of 1,080 rows** draw their key from a row whose sealed-anchor delivered scenario
  equals their own, confirming the within-delivered-scenario bucketing; note this read's scenario
  key is the coarse scenario prefix of the parsed delivered intent, which is one notch coarser than
  the generator's own bucket labels (its provenance names `(unparsed)`, `(residual, borrowed)` and
  `recommendation_locations` buckets), so this is agreement under a coarser partition, not a
  reconstruction of the generator's buckets.
- **The strongest integrity statement available.** On **1,080 of 1,080 rows the twin's twenty
  supplied values are exactly the twenty the arm supplied to the key's source row.** The store,
  the k, the fuse and the rank policy are therefore provably identical and the only thing that
  moved is which row's speech asked the question.

## Cost and duty cycle

| Figure | Twin | B1 arm | Anchor | Direct | Registered ceiling |
| --- | ---: | ---: | ---: | ---: | ---: |
| Generation contacts (per row) | 5,429 (5.027) | 5,425 (5.023) | 5,417 (5.016) | 1,080 (1.00) | 11,880 (11) |
| Repeated speech seconds | 15,492.58 | 15,494.60 | 15,459.76 | 3,084.53 | 33,930 |
| Prompt / completion tokens | 49,264,418 / 254,006 | 49,388,949 / 255,524 | 45,998,267 / 255,153 | 2,459,915 / 26,764 | -- |
| Native task-contract tool calls | 1,082 | 1,084 | 1,082 | 0 | 6,480 |
| FIT receipts / endpoints | 5,429 / 21,716 | 5,425 / 21,700 | -- | -- | -- / 47,520 |
| GPU hours (monitor active seconds) | 3.6369 (13,092.89 s) | 3.6819 (13,254.97 s) | 3.3880 (12,196.65 s) | 0.0871 | 12.0 |
| Generation wall seconds | 13,800.7 | 13,894.2 | not in its receipts | 450.6 | -- |
| Slot occupancy; utilisation; parked | 0.881; 90.35 %; 0.051 | 0.877; 91.01 %; 0.045 | --; 88.73 %; 0.022 | 0.658; 55.66 %; 0.281 | -- |
| Mean latency (s); preprocess (s, workers) | 8.954; 10.56 at 8 | 8.982; 10.01 at 8 | -- | 1.098; 13.03 at 8 | -- |
| Official scoring jobs (seconds) | 1 (384.53) | 1 (166.22) | -- | -- | 1 |

Every registered ceiling held with room: 45.7 % of the contact ceiling, 45.7 % of the speech
ceiling, 30.3 % of the GPU-hour ceiling, 45.7 % of the FIT-endpoint ceiling and 16.7 % of the
task-contract ceiling. The twin costs **4 more contacts, 2.0 fewer repeated speech seconds and
124,531 fewer prompt tokens (-0.25 %) than the arm**, which is the token-matching claim confirmed
on the wire rather than on the snapshot: two flights that differ only in which vector keyed the
retrieval spend the same budget. Against the anchor the twin adds +3,266,151 prompt tokens
(+7.10 %) for 12 more contacts.

FIT: `every_request_fits = true` on all 5,429 receipts; minimum margin **7,707 tokens** in the
`reviewer` phase against the 24,576-token slot. One honest note: the twin's widest realised request
needed **16,869** tokens, which is **404 tokens above the preregistration's section-9 upper bound
of 16,465** (built from the anchor's realised per-role-visit maxima plus the largest exemplar
block) though below the same section's conservative static-supply bound of 17,018 and far below the
slot. The arm's widest was 15,976. The section-9 sum is a bound over *different rows and different
role visits* and the preregistration itself recorded that the static render under-counts the later
Reviewer and Planner requests; the FIT receipt is the per-request authority and it says every
request fit.

## The harness-admission consequence

The cell B1 verdict's proposed entry is now complete. The module, the class, the key, the ON form
and the class's own registered null are unchanged from that verdict; this read supplies the missing
clause-1b evidence.

- **module**: exemplar supply to the Solver (`train-exemplars` store)
- **class**: `stores`, **key**: `knowledge_stores.train-exemplars`
- **on**: release `171aa4a82c2b15fff2c72e907ea80298be8d72309cca0d7367eb50debb042129`, snapshot
  content hash `4c498dc0282055b9fe036ed7e950af519bd48b5f26e76876d0250727196a72e9`, plain
  top-k = 20, `saea-fuse-supplyfilter-v1` at m = c = top_l = 20,
  `saea-rank-wcos-prior-agree-v1` with w_cos = 1, tau 0.0, keyed by the row's own sealed
  full-utterance speech vector in the `content` dimension
- **off (null form)**: the named store absent from the `knowledge_stores` mapping, the `stores`
  class's own registered null (`rails.config_tables.is_stores_null_arm`)
- **evidence**: the cell B1 verdict plus this verdict; sealed scores `a7105b32...` (arm) and
  `7e8b995e...` (twin); paired reads `a6430288...` and
  `37cec40d539df80eb02e9b45f8965669105f2a91588dafbf0d921aa526d02d1a`
- **status**: **ADMITTED, provisional** -- the preregistered rule now passes in full, but the
  2026-09-08 family rule still requires a replicate or a named root cause before a module is
  frozen, and no request-identical replicate of this arm exists. The row is **not written by this
  read**: the coordinator owns the admission receipt and
  `scripts/checks/harness_admission_check.py` is its oracle.

## What is not claimed

- **No superiority, generalization, paper-scale or held-out claim.** TRAIN Fold A is an exposed
  discovery roster; nothing is said about Fold B, DEV-1000 or the test split, which stay unread.
- **The twin is a retrieval-key control, not an information-free control.** Twenty real annotated
  TRAIN exemplars still reach the Solver in the twin arm, and its +4.77 pp over the anchor is the
  measurement of exactly that. Nothing here says what an arm with *no* exemplars and matched tokens
  would do; no such arm exists.
- **The additive decomposition is a point estimate.** "37.8 % presence, 62.2 % key" has no interval
  attached and should not be quoted as one.
- **The twin's own gain is not registered as a module.** Owner decision 18 conditions that
  registration on branch B, and branch A was reached. If a later read wants module M1p, it needs
  its own registration.
- **No component-causal attribution below the store.** One store, one k, one fuse policy, one rank
  policy, one release; this pair of cells cannot say which is load-bearing, only that the key is.
- **One pass each.** The margins are cell B0r's own null, measured on the same roster and geometry
  but on a different configuration, and the anchor leg is a single realization shared with every
  cell built on it. Greedy decoding at temperature 0 is not bitwise reproducible across batch
  compositions, so arm and twin trajectories differ row by row for reasons other than the key; the
  paired bootstrap prices that variation but does not remove it.
- **Nothing about the review loop**, which is held identical across all three arms here. The twin's
  nine executed revisions against the arm's seven and the anchor's five are recorded, not
  attributed.
- **A2's availability numbers are not predictions of the delivered answer**, and the twin makes the
  point twice over: 40 rows were available through its coverage lever and 2 were converted.

## Exposure

**Zero model contacts; the sealed bytes were copied, never opened for writing.** This read made no
model, tokenizer, encoder, ASR or server contact and touched no serving session, flight worktree or
flight lock. The only scorer invocations are the model-free projection-v3 and TRAIN symmetric
scorings, four arms each, every one over a COPY of that arm's sealed `outputs.jsonl` written under
`SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-B1-TWIN-PAIRED-ANALYSIS-V1/`. No sealed file was opened for
writing, moved or renamed; no exposure-ledger row, harness-admission receipt or results ledger was
edited by this read. Execution profile `model-free-check`.
