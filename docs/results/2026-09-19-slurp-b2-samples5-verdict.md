# Cell B2 v3: grouped Solver sampling (module M2) on the sealed anchor, TRAIN A

Status: **NEUTRAL on the official number (48.60 / 78.80); non-inferiority on pooled SLU is NOT
PROVEN at the request-identical own-null margin.** Cell B2 v3 reads **48.5977** official pooled
SLU-F1 and **78.7963** official intent against the sealed dual-store anchor's 48.5336 / 77.9630.
The gating contrast is a dead level on the primary metric -- **+0.0641 pp** pooled SLU with a CI95
of **[-1.4598, +1.5979]** -- while every label metric rises by about the own null's width and every
entity metric falls: intent **+0.8333** [-0.3000, +1.8797], scenario **+1.0185** [+0.0000,
+1.9851], action **+0.7407** [-0.4197, +1.8416], against per-row exact slot F1 **-0.5639**
[-1.9305, +0.8209] and per-row SLU-F1 **-0.9037** [-2.0488, +0.2775]. The registered ADMITTED rule
fails on its first clause (the pooled SLU CI95 lower bound does not clear zero) and the registered
HARMFUL clause does not fire (the pooled SLU CI95 upper bound +1.5979 is far above -h_SLU and the
intent CI95 lower bound -0.3000 is above -h_intent), so the mechanical status is **NEUTRAL**. Under
owner decision 8, restated by decision 15, the greedy-repeat twin flies only on a positive arm
CI95: **the twin is NOT due, the arm-versus-twin clause is NOT REACHED, and the cell closes without
it.** Root: the B2 v3 paired-read agent, 2026-09-19. Program:
`docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md` (section 4, module M2, items
E2, E2b, E2c, E2d). Preregistration:
`docs/readiness/2026-09-17-slurp-b2-samples5-anchor-v3-preregistration.md`, with the one
root-diagnosed recovery recorded in
`docs/readiness/2026-09-17-slurp-b2-samples5-anchor-v3-recovery-v1.md` -- that recovery is the
four-row **smoke's**; **the arm itself is the first and only arm attempt**. Margins: the TRAIN A own
null of cell B0r, **h_SLU = 1.1218 pp** and **h_intent = 1.0051 pp** at CI95
(`docs/results/2026-09-17-slurp-b0-review-off-redecision-v2.md`).

## What flew

One arm, one attempt, no recovery at the arm level. Run
`SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-TRAIN-FOLD-A-V3`, attempt
`attempt-slurp-native-samples5-anchor-train-fold-a-generation-v3`, FINALIZED, manifest
**COMPLETED** at study commit `b97260ed330e72bd09065cf109fecbfc32ed58a7`, composed config
`9688e0c9e6e93e30d200469b6ecafd28f865a37f0b0a3d694a879f7749f426a3`, protocol
`4e5acfad5219ef6920b881dec240ead02d06f53aaf91895e92674579f0ee0a3e` -- the exact values the
preregistration's section 2 pinned -- arm `speech-feature-query-native-tools`, profile
`bounded-discovery-probe`, split identity
`61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, role `discovery`, attached to
the resident session `serving-slurp-native-candidate-five-train-a-np4-v1`, one official complete
scoring job.

The one factor against the sealed anchor lives in one channel, `native_episode.roles.solver`: the
Solver visit becomes a **grouped** visit of **five** samples at **temperature 0.7** on the five
pinned seeds `1249110493 .. 1249110497`, aggregated by the registered deterministic commit policy
`saea-commit-plurality-support-v1` at **min_support 3 of 5** and **char-F1 0.8**, with the policy
fragment moving from `phase-native-candidates-review-revise-v1` to
`phase-native-candidates-review-revise-samples5-v1` (`max_contacts` 11 to 19). Under E2c the
committed aggregate is the ONE `phase:solver` state the Reviewer and the Planner read, so the
review loop sees one draft exactly as it does on the anchor. Held identical to the anchor: the
roster, the split, the model fragment, the np4 / 24,576-token geometry, both knowledge stores, the
four-candidate supply contract, every instruction template, the role graph (reviewer 3 / planner 1
/ `max_revisions` 1, `deliver-latest-solver`) and the scorers.

Rows: 1,080 scored per arm; **parsed 1,080 B2 v3**, 1,073 anchor, 1,080 direct. The arm delivers a
parseable answer on every row where the anchor delivered seven unparseable ones: a plurality over
five samples is itself a parse-failure filter, and that is the first measured consequence of the
mechanism.

### Provenance

| Artifact | SHA-256 |
| --- | --- |
| B2 v3 `scores.json` | `0a69cbaa1cd9a5c00f4cd212d6ece43d96b30b4a80ce459dfb7eb6af6a4ef6a0` |
| B2 v3 `run-manifest.json` | `8ad47ef21d1bb62631d01bd61f67d0e6783a7ded9205a4613f6219d5893aedb9` |
| B2 v3 `outputs.jsonl` | `477b5b910adba332f0d71c889a4adae3d6f48945220c7622054d0b25db02b93c` |
| B2 v3 `trace.jsonl` | `e26af6df42822c9390404b46bb0b07c72562ff5d1b7e19e56230a4e757d68a6c` |
| B2 v3 `flight-receipts.json` | `39a9162f1c8091d3ba3a2e9cd7d064f0b5f82e96e327ac579886b3295cd20ee0` |
| anchor `scores.json` | `7360876322488e5fda689fcafda00e90da2ebf559e5a35e635c550f940202b47` |
| anchor `run-manifest.json` | `049ac230e536bc6c8fe45bc847756ba486c4904e9c7602c698157f78d70c0152` |
| anchor `outputs.jsonl` | `d87d71e8fa0fe93b45d5c6817ba125b016d8d91f44a14309171dd0f3a64270d8` |
| direct anchor `scores.json` | `7840a959fe4f43928fda0e0cacfe8c0ee4200116bfcd269bfe3451b59da29c38` |
| direct anchor `run-manifest.json` | `546109055a373b358c43d36878c532b95784ee5d73d07f011c5fa3ea3d7ce11e` |
| direct anchor `outputs.jsonl` | `5c182ddfc81effe2465fb58f052842538f22ead3601355dbe77427c937decd61` |
| roster `docs/receipts/rosters/slurp-evo-fold-a-v2.json` | `1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d` |
| roster metadata | `07f4cd83b83d83d65500a328e0a38421ede575195c63ae118def0d1006c14e34` |
| paired read `analysis/SAEA-SLURP-B2-SAMPLES5-PAIRED-ANALYSIS-V1/score-contrasts.json` | `7aeaccca0c20f7fa5da847c1a8f11119fbc81837f8264e1b292c1311064527a9` |

Every hash above was recomputed from the file before it was read, and the three the coordinator's
brief declared for the arm match byte for byte. The full input and output hash tables, including
the driver, the README, the per-scenario tables, the M2 diagnostics, the sensitivity table, the
slot decomposition, the revision scan and the cost block, are in that analysis directory's
`README.md` and `MANIFEST.json`.

The driver is an adapted copy of three sealed precedent drivers whose estimator calls are
reproduced byte for byte:
`analysis/SAEA-SLURP-B5E-COMBINATION-PAIRED-ANALYSIS-V1/b5e_paired_read.py`
(`0f5a60a8eb15c2ae641718c817ea103d2b456a17dd94ba3a4c9ae63db737db59`),
`analysis/SAEA-SLURP-B1-EXEMPLARS-K20-PAIRED-ANALYSIS-V1/b1_paired_read.py`
(`2644710aee90b62fa200aed847ddfda2544e776f4f59c57853e4fc7dd4479225`) and
`analysis/SAEA-SLURP-B4B-SLOT-STORE-V2-PAIRED-ANALYSIS-V1/b4b_paired_read.py`
(`80d6db58da00bfe1f48d4e2240d2e837bdb4300df3c9b08f02f14c1fa9258ce2`). Only the arm list, the
contrast list, the M2 diagnostic stage, the offline sensitivity stage and the decision block are
new; `analysis.null_calibration_cli.rows_for`, `analysis.null_calibration.pooled_f1`,
`analysis.paired.resampled_statistic` and `analysis.paired.paired_contrast` are unchanged. Paired
whole-speaker cluster bootstrap over the roster's 125 speakers, 10,000 draws, seed 20260915, CI95
for advancement and CI90 for diagnostics as percentiles of the same retained replicate sequence;
sensitivity the paired scenario-stratified row bootstrap (18 scenarios of 60) on the same draws and
seed.

## The STOP condition, closed before any B2 table was read

Four things had to reproduce from the sealed bytes before the arm's contrasts were opened.
**PASSED, with zero failures.**

1. **The arm's registered identity.** Composed config, protocol hash, study commit and manifest
   status all equal the preregistration's section-2 values.
2. **Both registered comparator official aggregates**, to better than 0.005 pp: anchor
   48.5336 / 77.9630 / 84.8148 / 79.2593 / 29.4976 against the registered 48.53 / 77.96 / 84.81 /
   79.26 / 29.50; direct 33.8851 / 73.7037 / 82.6852 / 75.0926 / 21.0976 against 33.89 / 73.70 /
   82.69 / 75.09 / 21.10. `analysis.null_calibration.pooled_f1` also reproduces every arm's own
   official pooled SLU and span F1 from its per-sample rows to 1e-6.
3. **The registered v3 and TRAIN symmetric readings of both comparators.** Anchor v3
   51.9946 / 79.3519 / 85.4630 / 80.6481 / 40.3025 against 51.99 / 79.35 / 85.46 / 80.65 / 40.30;
   direct v3 34.3137 / 75.3704 / 84.1667 / 75.9259 / 23.2359 against 34.31 / 75.37 / 84.17 / 75.93
   / 23.24. Anchor symmetric 52.0887 / 41.3830 against 52.09 / 41.38; direct symmetric 34.4582 /
   24.3763 against 34.46 / 24.38.
4. **The offline commit replay at the registered s = 3** reproduces the arm's own sealed official
   count fields on **1,080 of 1,080 rows** -- every `slu_f1_word_*`, `slu_f1_char_*` and
   `slot_f1_exact_*` field. That is what licenses reading s = 2 and s = 4 off the same instrument.

## B2 v3 minus the sealed anchor -- the gating contrast (percentage points)

| Metric | Anchor | B2 v3 | Delta | Speaker CI95 | Speaker CI90 | Scenario-stratified CI95 | Equal-scenario |
| --- | ---: | ---: | ---: | --- | --- | --- | ---: |
| Official pooled SLU-F1 | 48.53 | 48.60 | **+0.06** | [-1.46, +1.60] | [-1.22, +1.36] | [-1.59, +1.72] | +0.46 |
| Intent (scenario+action) | 77.96 | 78.80 | **+0.83** | [-0.30, +1.88] | [-0.10, +1.72] | [-0.28, +1.94] | +0.83 |
| Scenario | 84.81 | 85.83 | **+1.02** | [+0.00, +1.99] | [+0.19, +1.83] | [+0.00, +2.04] | +1.02 |
| Action | 79.26 | 80.00 | **+0.74** | [-0.42, +1.84] | [-0.22, +1.66] | [-0.37, +1.85] | +0.74 |
| Official pooled span F1 | 29.50 | 29.50 | **-0.00** | [-2.13, +2.06] | [-1.79, +1.74] | [-2.53, +2.52] | +0.44 |
| Exact slot F1 (row mean) | 19.02 | 18.46 | **-0.56** | [-1.93, +0.82] | [-1.71, +0.59] | [-2.17, +1.05] | -0.56 |
| SLU-F1 (row mean) | 30.29 | 29.39 | **-0.90** | [-2.05, +0.28] | [-1.87, +0.09] | [-2.19, +0.38] | -0.90 |

Saves / harms / ties with the exact two-sided McNemar p: intent 24 / 15 / 1,041 (**0.200**);
scenario 22 / 11 / 1,047 (0.080); action 23 / 15 / 1,042 (0.256); exact slot F1 65 / 71 / 944
(0.668); row SLU-F1 107 / 127 / 846 (0.214). **Not one of the seven intervals excludes zero at
CI95 and not one of the five sign tests rejects.** The scenario interval's lower bound is exactly
+0.0000 and its CI90 clears zero ([+0.19, +1.83]); the registered clauses read CI95 and are applied
as registered.

The shape of this contrast is the finding, and it is not a null result dressed up. **The mechanism
moves two things in opposite directions.** Labels go up by roughly the own null's half-width on all
three label metrics at once (intent +0.83, scenario +1.02, action +0.74), which is what a plurality
vote over five independent draws is supposed to buy. Entities go down (row SLU-F1 -0.90, exact slot
F1 -0.56), which is what a support filter costs when it drops true mentions along with false ones.
The pooled official metric is their sum, and their sum is zero.

## B2 v3 minus the released direct anchor (secondary, never a gate)

| Metric | Direct | B2 v3 | Delta | Speaker CI95 | Saves / harms / ties | McNemar p |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| Official pooled SLU-F1 | 33.89 | 48.60 | **+14.71** | [+11.80, +17.62] | -- | -- |
| Intent (scenario+action) | 73.70 | 78.80 | **+5.09** | [+2.98, +7.17] | 126 / 71 / 883 | 1.09e-4 |
| Scenario | 82.69 | 85.83 | **+3.15** | [+1.23, +5.25] | 91 / 57 / 932 | 6.48e-3 |
| Action | 75.09 | 80.00 | **+4.91** | [+2.84, +7.11] | 119 / 66 / 895 | 1.19e-4 |
| Official pooled span F1 | 21.10 | 29.50 | **+8.40** | [+4.95, +11.84] | -- | -- |
| Exact slot F1 (row mean) | 10.72 | 18.46 | **+7.74** | [+5.65, +9.89] | 151 / 52 / 877 | 2.19e-12 |
| SLU-F1 (row mean) | 16.06 | 29.39 | **+13.33** | [+11.30, +15.49] | 290 / 86 / 704 | 5.79e-27 |

Equal-scenario: pooled SLU +13.56, span F1 +8.04. The system-over-direct margin on pooled SLU is
**+14.71** against the anchor's own +14.65 -- the agent system's advantage over the direct baseline
is intact and essentially unchanged by this module. One honest note carried forward, exactly as the
B1, B4b and B5e verdicts carried theirs: against the **direct** anchor owner decision 17's
diagnostic flags `general` (net harmed +9) and `general` is also the one scenario whose paired
intent CI95 upper bound lies below zero ([-26.99, -2.00]). **The band is a clause of the rule only
against the sealed anchor, where 0 of 18 scenarios breach it.**

## The rule, applied unchanged

Owner decision 25 of 2026-09-18 changed the HARMFUL trigger for **combination** cells only and
states that single-factor admission clauses are unchanged; the B5e addendum repeats it ("The
single-factor admission clauses are unaffected"). Cell B2 is a single-factor cell, so both its
ADMITTED clauses and its HARMFUL clause are read exactly as registered. Owner decision 23 makes
every clause read the OFFICIAL, unprojected `slurp-slu-official-train` number.

| Clause | Requirement | Value | Threshold | Passes |
| --- | --- | ---: | ---: | --- |
| a | CI95 lower bound of the pooled official SLU delta vs the anchor > 0 | **-1.4598** | 0 | **NO** |
| b | intent CI95 lower bound > -h_intent | -0.3000 | -1.0051 | **YES** |
| c (symmetric) | the TRAIN symmetric scorer agrees in sign with the official delta | -0.2256 vs +0.0641 | same sign | **NO** |
| c (v3) | projection v3 agrees in sign with the official delta | -0.0008 vs +0.0641 | same sign | **NO** |
| d | no scenario's paired intent CI95 upper bound vs the anchor below zero | 0 of 18 breaching | CI95 upper < 0 | **YES** |
| **ADMITTED** | **all of the above** | -- | -- | **NO** |
| HARMFUL | pooled SLU CI95 **upper** < -h_SLU **or** intent CI95 **lower** < -h_intent | +1.5979 / -0.3000 | -1.1218 / -1.0051 | **no** |
| NEUTRAL | otherwise, while non-inferior on both; enters the default plan only if it lowers cost | 9.08 contacts/row vs 5.02 (1.81x) | < 1.0x | **does not lower cost** |

**Status: NEUTRAL.** Read once, from the single official score of the complete manifest; no repeat,
no re-score, no row filtering.

**The honest statement the NEUTRAL hides, and this verdict does not hide it.** Non-inferiority on
pooled SLU is **NOT PROVEN**: the contrast's CI95 lower bound, -1.4598, lies below -h_SLU =
-1.1218. The registered HARMFUL clause is written on the pooled SLU CI95 *upper* bound and
therefore does not fire, and it is applied as registered -- but "NEUTRAL" here means "no measured
harm and no measured gain", not "proven equivalent". Intent non-inferiority **is** proven (CI95
lower -0.3000 > -1.0051). The structural reason is the one owner decision 25 and the B5e addendum
already named: h_SLU and h_intent are the CI95 half-widths of (B0r minus B0), two byte-identical
configurations differing only in batch composition -- the narrowest interval this roster can
produce. This contrast's own pooled SLU half-width is **1.5289 pp** against that 1.1218 pp margin,
so at a true effect of zero its lower bound crosses -h by construction. The margin is doing what
the addendum predicted; the point estimate is +0.06.

**The sign-agreement clauses fail, and they fail in the least interesting way possible.** The
official delta is +0.0641, the v3 delta -0.0008 and the symmetric delta -0.2256. All three are far
inside their own intervals and all three are, for practical purposes, zero; the sign simply is not
stable across three scorings of the same sealed bytes when the effect is this small. That is
evidence that the pooled effect is nil, not evidence of a disagreement between scorers. The clause
is applied as registered and recorded as failed.

**The twin.** Owner decision 8, restated by decision 15, launches the greedy-repeat twin only after
the arm shows a positive CI95 against the base. The arm's CI95 lower bound is -1.4598. **The twin
is not due, it does not fly, and the arm-versus-twin clause of the ADMITTED rule is reported as NOT
REACHED.** The cell closes here. The consequence is stated plainly under "What is not claimed":
without the twin, nothing in this read separates "five samples at temperature 0.7 plus aggregation"
from "five greedy repeats plus aggregation".

## Every scenario, B2 v3 minus the sealed anchor (natural mixture; equal-scenario mean last)

| Scenario | n | Anchor SLU | B2 SLU | Delta | Anchor intent | B2 intent | Delta | Intent CI95 | Net harmed | Flag | Beyond band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | --- |
| alarm | 60 | 52.66 | 45.24 | **-7.42** | 83.33 | 90.00 | +6.67 | [+1.39, +14.71] | -4 | no | no |
| audio | 60 | 47.75 | 48.63 | +0.88 | 76.67 | 80.00 | +3.33 | [+0.00, +5.66] | -2 | no | no |
| calendar | 60 | 48.38 | 45.76 | -2.61 | 75.00 | 76.67 | +1.67 | [+0.00, +5.66] | -1 | no | no |
| cooking | 60 | 62.47 | 63.32 | +0.85 | 85.00 | 85.00 | 0.00 | [-4.69, +4.84] | +0 | no | no |
| datetime | 60 | 59.52 | 57.48 | -2.03 | 83.33 | 86.67 | +3.33 | [-3.23, +9.84] | -2 | no | no |
| email | 60 | 36.64 | 41.22 | +4.59 | 85.00 | 88.33 | +3.33 | [+0.00, +8.47] | -2 | no | no |
| general | 60 | 15.45 | 16.97 | +1.52 | 36.67 | 31.67 | **-5.00** | [-13.12, +1.75] | +3 | no | no |
| iot | 60 | 55.53 | 67.04 | **+11.50** | 86.67 | 85.00 | -1.67 | [-5.08, +0.00] | +1 | no | no |
| lists | 60 | 43.55 | 39.96 | -3.59 | 83.33 | 83.33 | 0.00 | [-4.84, +5.08] | +0 | no | no |
| music | 60 | 34.53 | 41.88 | **+7.35** | 76.67 | 73.33 | -3.33 | [-10.17, +3.28] | +2 | no | no |
| news | 60 | 44.24 | 42.06 | -2.18 | 80.00 | 80.00 | 0.00 | [+0.00, +0.00] | +0 | no | no |
| play | 60 | 46.82 | 43.43 | -3.40 | 58.33 | 63.33 | +5.00 | [-5.17, +16.39] | -3 | no | no |
| qa | 60 | 57.04 | 56.98 | -0.05 | 75.00 | 75.00 | 0.00 | [+0.00, +0.00] | +0 | no | no |
| recommendation | 60 | 49.75 | 44.85 | **-4.90** | 90.00 | 90.00 | 0.00 | [+0.00, +0.00] | +0 | no | no |
| social | 60 | 34.74 | 42.08 | **+7.34** | 66.67 | 66.67 | 0.00 | [+0.00, +0.00] | +0 | no | no |
| takeaway | 60 | 48.84 | 48.35 | -0.49 | 85.00 | 83.33 | -1.67 | [-5.08, +0.00] | +1 | no | no |
| transport | 60 | 51.34 | 53.77 | +2.43 | 86.67 | 86.67 | 0.00 | [+0.00, +0.00] | +0 | no | no |
| weather | 60 | 53.81 | 52.32 | -1.49 | 90.00 | 93.33 | +3.33 | [+0.00, +8.62] | -2 | no | no |
| **equal-scenario mean** | 18 | | | **+0.46** | | | **+0.83** | | | | |

**No scenario loses intent beyond the band (0 of 18) and no scenario reaches owner decision 17's
five-row flag**; the worst net figure is +3 on `general`. Nine scenarios gain pooled SLU and nine
lose it, with large offsetting swings -- `iot` +11.50, `music` +7.35, `social` +7.34 against
`alarm` -7.42, `recommendation` -4.90, `lists` -3.59. The equal-scenario weighting (+0.46 SLU,
+0.83 intent) agrees in sign with the natural mixture (+0.06, +0.83), so the pooled nil is not a
single-stratum artifact; it is a genuine cancellation across strata.

## Projection v3 and the TRAIN symmetric view, beside the rule

Owner decision 23 puts every clause on the official unprojected number; projection v3 (owner
decision 7) and the TRAIN symmetric sibling (owner decision 14) are the sign-agreement clause and
are otherwise reported beside. Each arm's sealed `outputs.jsonl` was COPIED under the analysis
directory and the registered scorers read the copy. **Both comparators reproduce their registered
readings exactly**, which is what licenses reading B2's numbers beside them.

| Arm | Official SLU | Official intent | v3 SLU | v3 intent | v3 span F1 | Symmetric SLU | Symmetric span F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| anchor | 48.53 | 77.96 | 51.99 | 79.35 | 40.30 | 52.09 | 41.38 |
| **B2 v3** | **48.60** | **78.80** | **51.99** | **79.91** | **39.71** | **51.86** | **40.61** |
| direct | 33.89 | 73.70 | 34.31 | 75.37 | 23.24 | 34.46 | 24.38 |

Contrasts against the anchor: **v3 SLU -0.0008 [-1.74, +1.78]**, v3 intent +0.5556 [-0.44, +1.52],
v3 span F1 -0.5975; **symmetric SLU -0.2256 [-1.95, +1.55]**, symmetric intent +0.8333 [-0.30,
+1.88], symmetric span F1 -0.7704. Against the direct anchor: v3 SLU +17.68, symmetric SLU +17.41.
The symmetric intent equals the official intent exactly because the normaliser touches fillers and
not labels; the v3 intent differs because v3 projects labels too. **Every view agrees that the
pooled SLU effect is nil and that intent rises by well under a point**; no interval changes any
verdict, and the sign flip between the three views at a point estimate of ~0.06 is the reason
clause (c) is recorded as failed rather than as a substantive disagreement.

## The mandatory M2 diagnostics

The instrument is the sealed `solver_group` custody of each row, re-read with the registered commit
policy's own code (`rails.commit_policies`), plus each row's sealed `native_episode_receipt`. No
filler, response or utterance text is retained anywhere in this read.

**Custody is complete on every row.** All 1,080 rows carry a `solver_group`; all 1,080 carry five
samples; all 1,080 carry the five declared seeds `1249110493..1249110497`; all 1,080 carry
temperature 0.7; all 1,080 carry `commit_policy_id` `saea-commit-plurality-support-v1` and the E2d
`commit_params` {min_support 3, similarity_threshold 0.8}; and on all 1,080 the group's five
contacts are the final Solver visit's. Re-applying the registered policy to the sealed samples
reproduces the sealed delivered intent on **1,080 of 1,080 rows**.

**Parse.** 29 malformed samples of 5,400 (**0.54 %**), spread over 13 rows (five rows with one
malformed, three with two, two with three, three with four). **No row had all five malformed**,
which is exactly why the arm delivers a parseable answer on all 1,080 rows against the anchor's
1,073. Sample 0 was malformed on 6 rows.

**Sample agreement and intent support.** The committed intent's support among the five samples:

| Agreeing samples | Rows | Delivered intent correct | Accuracy |
| ---: | ---: | ---: | ---: |
| 5 of 5 | 1,012 | 824 | **81.42 %** |
| 4 of 5 | 26 | 10 | 38.46 % |
| 3 of 5 | 33 | 11 | 33.33 % |
| 2 of 5 | 6 | 3 | 50.00 % |
| 1 of 5 | 3 | 3 | 100.00 % |

Mean agreeing samples **4.887**; **1,012 rows (93.7 %) are unanimous**. The 68 non-unanimous rows
deliver a correct intent on 27 of 68 (**39.7 %**) against 81.4 % on the unanimous ones. **Sample
agreement is a strong, free confidence signal** -- a 41-point accuracy gap, available at zero extra
contacts from custody the harness already seals. That is the most reusable thing this cell
produced, and it is a diagnostic here, not a claim.

Plurality margins (best count minus runner-up): 5 on 1,012 rows, 4 on 4, 3 on 25, 2 on 2, 1 on 33,
0 on 4. **37 rows were decided by a bare plurality** (margin <= 1) and the registered lowest-index
tie-break was actually used on **4** rows. Distinct intents per row: one on 1,024 rows, two on 53,
three on 3.

**What the commit actually changed.** The delivered answer differs from sample 0 on **252 rows
(23.3 %)**, but the delivered *intent* differs from sample 0's on only **13**. The commit policy is
overwhelmingly an entity filter, not an intent chooser.

**The entity support filter.** Across the roster the policy formed 1,771 same-type clusters and
delivered **822** of them: **949 clusters were dropped** at support < 3 (640 singletons, 309 pairs),
removing **1,258 mentions**; 3,545 mentions survived in the kept clusters. Kept-cluster support:
460 at 5 of 5, 152 at 4, 209 at 3, and one cluster of 10 mentions. The delivered filler is the
cluster medoid: it came from sample 0 on **702** of 822 clusters, sample 1 on 95, sample 2 on 20,
sample 3 on 3 and sample 4 on 2, and **815 of 822 medoid selections involved a tie** in mean
similarity resolved to the lowest sample index -- that is, the cluster members were usually the same
string. The types losing the most clusters to the filter: `time` 120, `device_type` 90,
`media_type` 43, `place_name` 41, `food_type` 40, `person` 38, `change_amount` 35, `date` 31.

**Spurious-entity suppression, against the anchor.** This is the mechanism the preregistration
predicted (section 1: entity false positives "are exactly what a support filter over independent
samples can suppress"). It worked, and it is priced.

| Roster total | Anchor | B2 v3 | Delta |
| --- | ---: | ---: | ---: |
| Gold mentions | 941 | 941 | fixed |
| Predicted mentions | 910 | **822** | **-88** |
| Exact mentions | 272 | 260 | -12 |
| Different-filler mentions | 276 | 259 | -17 |
| Omitted mentions | 393 | **422** | **+29** |
| Spurious mentions | 362 | **303** | **-59** |
| FP mass | 1,131.23 | **978.90** | **-152.32** |
| FN mass | 1,193.23 | 1,216.90 | **+23.68** |
| Filler-distance (surface) mass | 407.23 | 372.90 | -34.32 |
| Empty-gold rows emitting entities (of 414) | 184 | **161** | **-23** |
| Mentions emitted on empty-gold rows | 198 | **173** | -25 |

**The filter removed 59 spurious mentions and 152 points of false-positive mass, and cut
entity-emitting empty-gold rows from 184 to 161 -- and it paid for that with 29 more omissions and
12 fewer exact mentions.** The two almost exactly cancel in the pooled metric. Per type, the
largest FP-mass reductions are `device_type` -21.93, `house_place` -18.82, `song_name` -13.76,
`radio_name` -12.27 and `business_name` -11.80; the largest regressions are `date` (+10.91 FP,
+12.91 FN), `event_name` (+5.82 FP, +11.82 FN), `media_type` (+6.21 FP) and `time` (+11.59 FN).

**The review loop under the grouped commit**, beside the anchor's:

| Quantity | B2 v3 | Anchor | Anchor registered baseline |
| --- | ---: | ---: | ---: |
| Rows with a Planner REVISE token | **11** | 5 | 5 |
| Rows with a second Solver visit (revisions executed) | **11** | 5 | 5 |
| Rows whose intent changed across the revision | **6 of 11** | **2 of 5** | 2 |
| Planner token histogram (ACCEPT / REVISE / OTHER) | 1,080 / 11 / 0 | 1,079 / 6 / 0 | -- |
| Contacts-per-row histogram | 9: 1,068; 17: 11; 8: 1 | 5: 1,072; 9: 5; 4: 3 | -- |
| Reviewer task-contract tool calls | **1,090** | 1,082 | 1,082 |

**The anchor's registered baseline of five executed revisions and two intent changes reproduces
exactly**, from its own sealed receipts and a targeted scan of its sealed trace. The arm executes
**11** revisions against the anchor's 5 -- the Planner asks for a second pass more than twice as
often -- and 6 of those 11 changed the intent. The loop is the anchor's throughout and is not
ablated here, so this is recorded and not attributed: a grouped Solver visit costs five contacts,
so each of those 11 revisions costs five more, which is the whole of the 17-contact tail.

## The REPORTED-ONLY offline sensitivity table

`analysis.native_commit_replay.replay_row` re-aggregates each sealed row's five raw samples at
s in {2, 3, 4} at char-F1 0.8, zero model contact, and the official scorer's own matching functions
score the result. At the registered s = 3 the reconstruction reproduces the arm's sealed official
count fields on all 1,080 rows, which is what licenses the other two rows.

| s | Pooled SLU-F1 | Intent | Scenario | Action | Pooled span F1 | Delivered mentions |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 46.5197 | 78.7963 | 85.8333 | 80.0000 | 29.1506 | 1,131 |
| **3 (registered)** | **48.5977** | **78.7963** | **85.8333** | **80.0000** | **29.4952** | **822** |
| 4 | 46.2156 | 78.7963 | 85.8333 | 80.0000 | 28.4427 | 613 |

**This table is reported and is never a gate.** The verdict is read at s = 3, char-F1 0.8, as fixed
before any contact (preregistration section 4), and no threshold may be chosen from it after the
fact (section 11). Two observations, both descriptive: the labels are identical at every s, because
s touches only the entity commit and not the intent vote -- so nothing in the intent story depends
on this parameter; and the registered s = 3 happens to be the best of the three on pooled SLU, by
2.08 pp over s = 2 and 2.38 pp over s = 4. **That the preregistered value turned out to be the peak
of the three is a fact about this table and not a result**; it licenses no claim that s = 3 is
optimal, and a value chosen from this table after the fact would not be admissible under section 11.

## Cost and duty cycle

| Figure | B2 v3 | Anchor | Direct | Registered ceiling |
| --- | ---: | ---: | ---: | ---: |
| Generation contacts (per row) | **9,807 (9.081)** | 5,417 (5.016) | 1,080 (1.000) | 20,520 (19) |
| Repeated speech seconds | **28,047.72** | 15,459.76 | 3,084.53 | 58,607 |
| Prompt / completion tokens | **84,544,871 / 364,052** | 45,998,267 / 255,153 | 2,459,915 / 26,764 | -- |
| Reviewer task-contract tool calls | **1,090** | 1,082 | 0 | 6,480 |
| FIT receipts / endpoints | **9,807 / 39,228** | 5,417 / 21,668 | -- | -- / 82,080 |
| GPU hours (monitor active seconds) | **3.7139 (13,370.1 s)** | 3.3880 (12,196.6 s) | 0.0871 (313.5 s) | 12.0 |
| Generation wall seconds | **13,753.95** | -- | 450.60 | -- |
| Slot occupancy; utilisation; parked | **0.8635; 87.48 %; 0.0271** | --; 88.73 %; 0.0219 | 0.658; 55.66 %; 0.281 | -- |
| Mean latency (s); preprocess (s, workers) | **4.844; 15.26 at 8** | -- | 1.098; 13.03 at 8 | -- |
| Official scoring jobs (seconds) | **1 (171.28)** | -- | 1 (156.42) | 1 |

**Every figure the coordinator's brief quoted from the flight receipts is confirmed**: 9,807
contacts, 28,047.72 repeated speech seconds, 84,544,871 prompt tokens, 364,052 completion tokens,
1,090 tool calls, wall 13,754.0 s, occupancy 0.863, 3.714 GPU hours, utilisation 87.5 %, parked
0.027. Every registered ceiling held with room: **47.8 %** of the contact ceiling, **47.9 %** of the
speech ceiling, **30.9 %** of the GPU-hour ceiling, **16.8 %** of the task-contract ceiling, and one
official scoring job of one. The realized 9.081 contacts per row sits almost exactly on the
preregistration's "about 9.0 per row" estimate and at 47.8 % of the exact 19-contact bounded-graph
ceiling.

**The prompt-cache assumption behind the 12.0 GPU-hour ceiling is now measured, and it holds.** The
preregistration stated it as an assumption and not a proof: the five sibling Solver requests of one
visit share a cached prompt prefix on one slot, so the arm should cost far less GPU time than its
contact count suggests. Against the anchor the arm makes **1.81x the contacts** and carries
**1.84x the prompt tokens**, and it spends **1.096x the GPU hours** -- 3.7139 against 3.3880, a
**9.6 %** increase for an **81 %** increase in contacts. Mean latency is 4.844 s against the
anchor's per-contact cost at the same geometry. A contact-proportional estimate without any prefix
reuse was about 6.1 GPU hours; the arm spent 3.71. **The five siblings do reuse the prefill**, and
the ceiling had roughly 3x headroom rather than 2x.

**Prompt fit.** `every_request_fits = true` on all **9,807** receipts (39,228 endpoints); minimum
margin **9,417 tokens** in the `planner` phase against the 24,576-token slot. The widest realized
request needed **15,159 tokens** -- **below the anchor's own widest realized 15,382** and well
inside the preregistration's section-9 bound (the anchor's tightest measured point 15,382 plus the
deliberately conservative 5 x 512 = 2,560-token growth term, 17,942). That is E2c working exactly as
section 9 predicted: a grouped Reviewer, Planner or second-round Solver request carries the anchor's
own form -- exactly one `phase:solver` state per Solver visit -- so the committed aggregate is
*shorter* than the anchor's single raw draft rather than longer, because the support filter removes
mentions. The v2 package's withdrawn four-extra-state growth term is confirmed unnecessary.

## What is not claimed

- **No superiority, generalization, paper-scale or held-out claim.** TRAIN Fold A is an exposed
  discovery roster; nothing is said about Fold B, DEV-1000 or the test split, which stay unread.
- **NEUTRAL does not mean "nothing happened".** It means the registered pooled-SLU clause did not
  clear zero and the registered HARMFUL clause did not fire. The cell measurably moves labels up
  and entity mentions down; the pooled metric is their sum. The per-metric and per-type tables are
  the finding, and the pooled zero is not evidence that nothing moved.
- **Non-inferiority on pooled SLU is not proven**, and this verdict says so rather than letting
  "NEUTRAL" imply equivalence. The CI95 lower bound -1.4598 lies below -h_SLU = -1.1218. The
  registered HARMFUL clause is written on the CI95 upper bound for pooled SLU and is applied as
  registered.
- **No twin evidence, and the gap is structural.** The greedy-repeat twin did not fly and is not
  due. Nothing here separates what temperature 0.7 bought from what five greedy repeats plus the
  same aggregation would have bought; the preregistration's arm-versus-twin diagnostics, including
  the per-row sample-disagreement rate, are **not reached**.
- **No claim that N = 5, s = 3 or char-F1 0.8 is optimal.** One configuration flew. The offline
  s in {2, 3, 4} table is reported, licenses no verdict, and the fact that s = 3 is the best of its
  three rows is a property of that table only.
- **No component-causal attribution below the moved channel.** Sampling, the plurality intent vote
  and the support-filtered entity commit moved together in one policy; this cell cannot say which
  of the three paid and which charged, only that the first two look like the credit and the third
  like the debit.
- **The sample-agreement confidence signal is a diagnostic, not a module.** The 81.4 % / 39.7 %
  split is measured on this arm's own delivered answers; using it to gate or route anything is a
  different mechanism and would be its own registered cell.
- **Nothing about whether reviewing a sample set rather than one committed draft helps or hurts.**
  E2c removed that difference from this cell rather than measuring it, and owner decision 16 keeps
  that form dropped.
- **Nothing about the review loop**, which is held identical to the anchor here. That the arm
  executed 11 revisions against the anchor's 5 is recorded and not attributed.
- **One pass.** Greedy decoding at temperature 0 is not bitwise reproducible across batch
  compositions, so the arm and the anchor diverge row by row for reasons other than the moved
  channel; the paired bootstrap prices that variation without removing it.
- The 64.00 / 78.00 program bar is a **combination-cell** clause (owner decisions 19, 20, 23) and is
  not one of this cell's clauses. For context only: the arm reads 48.60 against 64.00 and 78.80
  against 78.00.

## The harness-admission consequence (a proposal for the coordinator)

This verdict does not write `docs/receipts/harness-admission.json`; the receipt is the
coordinator's to close and `scripts/checks/harness_admission_check.py` is its oracle. The entry
this verdict supports:

- **module**: grouped Solver sampling with a deterministic plurality/support commit (module M2: the
  Solver phase is sampled five times at temperature 0.7 on five pinned seeds and the five raw
  structured answers are aggregated into the one delivered answer by
  `saea-commit-plurality-support-v1` at min_support 3 of 5 and char-F1 0.8; under E2c the committed
  aggregate is the single `phase:solver` state the Reviewer and the Planner read)
- **carrier**: `slurp`
- **class**: **`episode`** -- see the naming point below
- **key**: `native_episode.roles.solver`, one dotted path on the closed allowlist
  `rails.config_tables.EPISODE_LEVEL_SWITCH_KEYS`
- **off**: the historical Solver role, which `rails.config_tables.is_episode_null_arm` recognises as
  this key's null arm -- `samples` absent (1), no `decoding_overrides`, no `commit`. That is the
  sealed anchor's own Solver role, so the OFF arm is the comparator itself and no separate OFF cell
  was flown.
- **on**: `samples` 5, `decoding_overrides` {temperature 0.7, seed_offset 0}, `commit` {policy
  `saea-commit-plurality-support-v1`, min_support 3, similarity_threshold 0.8}, with the policy
  fragment `phase-native-candidates-review-revise-samples5-v1` (`max_contacts` 19)
- **status**: **NEUTRAL** -- this table's status for no harm and no gain
- **status_basis**: the registered single-factor rule of the B2 v3 preregistration section 7,
  unchanged (owner decision 25 changed the HARMFUL trigger for combination cells only). Pooled
  official SLU-F1 48.5336 -> 48.5977, **+0.0641 pp, CI95 [-1.4598, +1.5979]**: the lower bound does
  not clear zero, so the module is not admitted; the HARMFUL clause does not fire (SLU CI95 upper
  +1.5979 not below -1.1218; intent CI95 lower -0.3000 not below -1.0051), so it is not refused.
  Intent +0.8333 [-0.3000, +1.8797] is non-inferior and its lower bound clears -h_intent. Sign
  agreement fails on both the TRAIN symmetric view (-0.2256) and projection v3 (-0.0008) at a point
  estimate of +0.0641 -- three readings of the same sealed bytes that are all nil. 0 of 18 scenarios
  breach the intent band and none reaches owner decision 17's flag. **Non-inferiority on pooled SLU
  is NOT proven** (CI95 lower -1.4598 < -1.1218, contrast half-width 1.5289 against a 1.1218
  request-identical margin), and the entry must say so rather than record a bare NEUTRAL.
- **evidence**: this verdict; the sealed score
  `0a69cbaa1cd9a5c00f4cd212d6ece43d96b30b4a80ce459dfb7eb6af6a4ef6a0`; the paired read
  `SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-B2-SAMPLES5-PAIRED-ANALYSIS-V1/` with
  `score-contrasts.json` `7aeaccca0c20f7fa5da847c1a8f11119fbc81837f8264e1b292c1311064527a9` and
  every other output hashed in its `README.md` and `MANIFEST.json`
- **not_admitted_for**: any default plan -- a NEUTRAL module enters the default plan only if it
  lowers cost, and at 9.081 contacts per row against the anchor's 5.016 (1.81x contacts, 1.84x
  prompt tokens, 1.10x GPU hours) this one raises it; any claim about N, s or the similarity
  threshold beyond the flown values; any claim about what temperature bought, which needs the
  unflown twin; any other roster or carrier; any paper-scale or generalisation claim.
- **provisional**: `state` **UNMET**, and it is a different obligation from an admitted module's. A
  NEUTRAL entry carries no replication debt for a gain it did not claim, but this one carries a
  **measurement** debt: the cell's own token-matched control did not fly, so the read cannot
  separate sampling from repetition. If the program ever wants M2 in a plan, the greedy-repeat twin
  -- or a request-identical replicate giving this configuration its own null -- is the first thing
  to fly, because the pooled interval here is 1.53 pp wide against a 1.12 pp margin calibrated on a
  request-identical pair.

**One naming point the coordinator must rule on before writing the row.** The coordinator's brief
and the program spec's section-3 module table both name M2's switch class **`judges`**. Three later
artefacts say **`episode`**, and they are the ones the code enforces: the B2 v3 preregistration's
section 3 calls `native_episode.roles.solver` "the `episode`-class switch key" and names
`rails.config_tables.is_episode_null_arm`; `rails/config_tables.py` lists
`native_episode.roles.solver` in `EPISODE_LEVEL_SWITCH_KEYS`; and the `saea-harness-admission-v3`
schema history in `docs/receipts/harness-admission.json` says the `episode` class was added
precisely "so the SLURP v2 base program's M0 (review-loop off), M2 (grouped-Solver sampling) and M1
... each have a home". The proposal above is therefore written as `episode`. The spec's M2 row is
the stale text and should be corrected in the same change that writes the receipt; this verdict
does not edit it.

## Exposure

**Zero model contacts; the sealed bytes were copied, never opened for writing.** This read made no
model, tokenizer, encoder, ASR or server contact and touched no serving session, flight worktree,
scheduled task or flight lock. The only scorer invocations are the model-free projection-v3 and
TRAIN symmetric scorings, three arms each, every one over a COPY of that arm's sealed
`outputs.jsonl` written under
`SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-B2-SAMPLES5-PAIRED-ANALYSIS-V1/`. The offline commit replay
at s in {2, 3, 4} reads the sealed `solver_group` custody in memory and writes nothing to any run
directory. Two sealed traces were streamed read-only for the pre-revision intent diagnostic, and
only the named contacts' response records were parsed -- to intent ids, which were kept, and text,
which was not. No sealed file was opened for writing, moved or renamed; no exposure-ledger row,
harness-admission receipt or results ledger was edited by this read. Execution profile
`model-free-check`.
