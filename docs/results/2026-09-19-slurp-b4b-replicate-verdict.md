# Cell B4b-rep: the request-identical same-roster replicate of cell B4b (module M4b, slot store v2), TRAIN A

Status: **REPLICATED and ADMITTED.** All three registered clauses pass on the second realisation:
the official pooled SLU-F1 delta against the sealed anchor is **+1.5403 pp with a CI95 of [+0.2992,
+2.9287]**, lower bound above zero; intent is non-inferior at **+0.6481 pp, CI95 [-0.6228,
+1.8734]**, lower bound above the registered -1.0051 margin; and projection v3 agrees in sign at
**+0.8463 pp**. The cell's own output -- the thing it exists to produce -- is the own null of the
**admitted** configuration, measured for the first time: **h_SLU_M4b = 1.3222 pp** and
**h_intent_M4b = 1.0682 pp** at CI95, against the 1.1218 / 1.0051 that cell B4b had to borrow from
the review-off geometry. Root: the B4b-rep paired-read agent, 2026-09-19. Program:
`docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md` (module M4b, cell B4b).
Preregistration: `docs/readiness/2026-09-17-slurp-b4b-replicate-v2-preregistration.md` (section 6,
fixed before contact), with the one root-diagnosed recovery taken in the resume-recovery form of
owner decision 22, registered in
`docs/readiness/2026-09-18-slurp-b4b-replicate-v2-resume-v1.md`. Authority: owner decision 13 of
`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`, with decisions 7, 17, 22 and 23
applied and decision 25 not applicable (it changes combination cells only, so this single-factor
replicate's clauses read exactly as registered). First pass:
`docs/results/2026-09-17-slurp-b4b-slot-store-v2-verdict.md`, which stands unchanged beside this
verdict.

## What flew

Run `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-REPLICATE-V2`, attempt
`attempt-slurp-native-slot-store-v2-anchor-train-fold-a-replicate-generation-v2-resume2`,
FINALIZED, manifest **COMPLETED** at study commit
`f2a2cb21de01e582311391675fb14555bb58604d` with `study_repo_dirt` empty, composed config
`a2d986c893923e25472e0ec775ebf3ffce905cb4edb1935c44efab13b40a7950`, protocol
`df67e8e1192aefa3a9ff7292625b7fa6bfbaa754aa4bcb2737466b4eb435ef0c` -- the values the resume
registration's section 8 pinned -- arm `speech-feature-query-native-tools`, profile
`bounded-discovery-probe`, split identity
`61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, role `discovery`, attached to
the resident session `serving-slurp-native-candidate-five-train-a-np4-v1`, one official complete
scoring job.

This is the **first real use of harness item E10** (owner decision 22): a **RESUME-RECOVERY**. The
first attempt aborted at 2026-09-18T02:40:20Z after 2,922 contacts when the inherited resident
server died with the session that owned it; a zero-contact second attempt aborted at preflight on a
prepared-artifact identity mismatch (fixed by E10b/E10c); the third attempt kept the predecessor's
580 COMPLETE rows and flew the remaining 500. No smoke was registered and none was needed: the
preregistration proved the rendered request byte-identical to cell B4b's on 1,080 rows x 4 phases in
three pairings, and the aborted attempt itself realised that form 2,922 times on this roster.

| Artifact | SHA-256 |
| --- | --- |
| scores.json | `7e39a28d7f7bcb04c3012102dd9392e8c070f7b058f4e3452d7dbb01dbcc9481` |
| run-manifest.json | `810ee83fa9e022dec7f9ce576cf0583e89efd411d4d0bbe549dfb82f5baa3a7e` |
| outputs.jsonl | `6cfc8a9c6886ac7247174b45d0a6a5eaf882eb723b30e307ae64f957c5dbe0d8` |
| predecessor trace (re-hashed on disk) | `ad7a78c77c26b8c7255e31fa897678b23609c9578933425b679594831e17c897` |
| paired read `analysis/SAEA-SLURP-B4B-REPLICATE-PAIRED-ANALYSIS-V1/score-contrasts.json` | `a83d0ba163bde043d6e41cd0f2d8654a360365e032a8d2605554424b580b23cf` |
| paired read `.../README.md` | `0951d74a94faebd1e4a40424be239dc8ef84de51d1a434e5d8e6f3eb6b4cb891` |
| paired read driver `.../b4b_replicate_paired_read.py` | `1fd7ec0c8a66b48800244b672ede152de0015b50b3ed9e92fe4537e0abceaef6` |

Rows: 1,080 scored, **1,079 parsed** (1 malformed retained -- exactly cell B4b's count, against the
anchor's 7). Comparators, never re-flown and never re-scored: the sealed dual-store anchor
`SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1` (the clause leg, scores
`7360876322...`), cell B4b itself `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-V2` (the
own-null leg, scores `751c529806...`) and the released direct anchor
`SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-SOURCE-RECOVERY-V1` (secondary, scores `7840a959fe...`).
Paired whole-speaker cluster bootstrap, 125 clusters, 10,000 draws, seed 20260915, CI95 for the
clauses and CI90 beside; sensitivity the paired scenario-stratified row bootstrap on the same draws
and seed.

## The STOP condition, closed before any B4b-rep table was read

Both halves passed before a single number of this cell was looked at.

1. **The three registered comparator aggregates reproduce** from the sealed bytes, official,
   projection v3 and TRAIN symmetric: anchor 48.53 / 77.96 / 84.81 / 79.26 / 29.50 and 51.99 /
   79.35 / 85.46 / 80.65 / 40.30 and symmetric 52.09 / 41.38; B4b 51.09 / 78.52 / 85.09 / 79.63 /
   32.40 and 54.05 / 79.72 / 85.93 / 80.83 / 41.85 and symmetric 54.26 / 43.99; direct 33.89 /
   73.70 / 82.69 / 75.09 / 21.10 and 34.31 / 75.37 / 84.17 / 75.93 / 23.24 and symmetric 34.46 /
   24.38. Every one to the hundredth.
2. **Cell B4b's own verdict table reproduces**, 12 rows x 5-8 fields, zero failures, and the
   preregistration's own four-decimal digits come back exactly: pooled SLU CI95 lower
   **+1.1293641973** against the registered **+1.1294**, intent CI95 lower **-0.7117437722**
   against the registered **-0.7117**, both inside the 0.0001 tolerance. The recomputed (B4b minus
   anchor) contrast is +2.5519 [+1.1294, +3.9770] on pooled SLU and +0.5556 [-0.7117, +1.8182] on
   intent, with saves/harms/ties 24/18/1038 -- cell B4b's published table, digit for digit.

The same sealed bytes under the same estimator and seed give one answer, and it is the published
one.

## The resume form, re-derived model-free

Owner decision 22 requires that a resumed manifest be auditable as a resume, not merely as a
manifest. Every claim below was re-derived from the bytes on disk with the harness's own readers
(`core.flight.resume.read_predecessor_attempt`, `core.flight.resume.kept_sample_ids_sha256`),
read-only; no run directory, attempt record or prepared artifact was written, moved or renamed.

| check | value |
| --- | --- |
| merged manifest rows / distinct / equal the registered roster | 1,080 / 1,080 / yes |
| manifest split ids equal the roster; status COMPLETED | yes / yes |
| declared kept / flown / partial | 580 / 500 / 4 |
| kept-ids SHA-256 re-derived from the manifest's own list | `45e9eeb3a80c2b448cd7eb3922de4c000e22c2f188448c786de6f0a076916049` |
| ... equals the manifest's declaration and the registered value | yes / yes |
| predecessor trace re-hashed on disk | `ad7a78c7...17c897`, equal to the declaration |
| predecessor trace records / contacts re-scanned | 16,338 / **2,922**, equal to the attempt record |
| predecessor rows with requests / COMPLETE / INCOMPLETE | 584 / **580** / **4** |
| **kept set equals the predecessor's COMPLETE set** | **yes** |
| the 4 INCOMPLETE ids equal the four the resume note names | yes |
| **kept rows carrying the predecessor's own delivered text (SHA-256, invariant I7r)** | **580 of 580** |
| flown rows taken from the predecessor | **0** |
| flown count / disjoint from kept / kept + flown = roster | 500 / yes / yes |
| flown covers every INCOMPLETE and every never-started row | yes / yes (496 never started) |
| merged rows whose recomputed delivered-text SHA-256 equals the sealed `response_text_sha256` | 1,080 of 1,080 |

Completeness is the episode's own terminal receipt and never a contact count: a request-count read
alone would have reported 577 complete and 7 partial, because three short rows finished their
episode in fewer than five contacts. The kept rows are the predecessor's bytes, not a re-rendering
of them.

## (a) B4b-rep minus the sealed anchor -- the clause contrast (percentage points)

| Metric | Anchor | B4b-rep | Delta | Speaker CI95 | Speaker CI90 | CI95 half-width | Scenario-stratified CI90 | Equal-scenario | B4b's first pass |
| --- | ---: | ---: | ---: | --- | --- | ---: | --- | ---: | ---: |
| Official pooled SLU-F1 | 48.53 | 50.07 | **+1.54** | [+0.30, +2.93] | [+0.49, +2.69] | 1.3148 | [+0.38, +2.70] | +1.68 | +2.55 |
| Intent (scenario+action) | 77.96 | 78.61 | +0.65 | [-0.62, +1.87] | [-0.39, +1.68] | 1.2481 | [-0.37, +1.67] | +0.65 | +0.56 |
| Scenario | 84.81 | 84.63 | -0.19 | [-1.21, +0.76] | [-1.03, +0.60] | 0.9826 | [-1.02, +0.65] | -0.19 | +0.28 |
| Action | 79.26 | 79.91 | +0.65 | [-0.67, +1.89] | [-0.45, +1.68] | 1.2760 | [-0.37, +1.67] | +0.65 | +0.37 |
| Pooled span F1 | 29.50 | 31.62 | +2.12 | [+0.48, +3.92] | [+0.74, +3.60] | 1.7173 | [+0.56, +3.68] | +2.30 | +2.91 |
| Exact slot F1 (row mean) | 19.02 | 20.14 | +1.12 | [-0.03, +2.42] | [+0.15, +2.20] | 1.2297 | [+0.02, +2.19] | +1.12 | +1.60 |
| SLU-F1 (row mean) | 30.29 | 31.54 | +1.25 | [+0.25, +2.33] | [+0.42, +2.16] | 1.0396 | [+0.28, +2.24] | +1.25 | +1.69 |

Saves / harms / ties with the exact two-sided McNemar p: intent 27 / 20 / 1,033 (p = 0.38); scenario
16 / 18 / 1,046 (0.86); action 27 / 20 / 1,033 (0.38); exact slot F1 55 / 37 / 988 (0.076); row
SLU-F1 110 / 66 / 904 (**1.1e-3**). The scenario-stratified sensitivity agrees everywhere: no
interval changes sign.

The shape of the gain is the first pass's shape at about **60 % of its size**. The three label
metrics -- intent, scenario, action -- again sit inside the null and are again not claimed; the slot
metrics again carry the effect, with pooled SLU-F1, pooled span F1 and per-row SLU-F1 all bounded
away from zero at CI95 and per-row exact slot F1 clearing zero only at CI90 (it cleared CI95 in the
first pass). Nothing about the direction moved; the magnitude did, and the next section is the
instrument that says how much of that is realisation noise.

## (b) B4b-rep minus cell B4b -- the own null of the admitted configuration (clause 2)

**These half-widths are OUTPUTS of this cell.** No value for either appears anywhere in the
registration, and neither could be chosen after the fact.

| Metric | B4b | B4b-rep | Delta | Speaker CI95 | **CI95 half-width (the measured margin)** | Speaker CI90 | Saves / harms / ties (p) |
| --- | ---: | ---: | ---: | --- | ---: | --- | --- |
| Official pooled SLU-F1 | 51.09 | 50.07 | -1.01 | [-2.26, +0.39] | **h_SLU_M4b = 1.3222** | [-2.07, +0.15] | -- |
| Intent (scenario+action) | 78.52 | 78.61 | +0.09 | [-0.97, +1.17] | **h_intent_M4b = 1.0682** | [-0.79, +0.99] | 17 / 16 / 1,047 (1.00) |
| Scenario | 85.09 | 84.63 | -0.46 | [-1.38, +0.42] | 0.8962 | [-1.23, +0.28] | 10 / 15 / 1,055 (0.42) |
| Action | 79.63 | 79.91 | +0.28 | [-0.70, +1.29] | 0.9979 | [-0.56, +1.13] | 18 / 15 / 1,047 (0.73) |
| Pooled span F1 | 32.40 | 31.62 | -0.78 | [-2.49, +1.20] | 1.8450 | [-2.23, +0.84] | -- |
| Exact slot F1 (row mean) | 20.62 | 20.14 | -0.48 | [-1.73, +0.85] | 1.2905 | [-1.54, +0.64] | 36 / 46 / 998 (0.32) |
| SLU-F1 (row mean) | 31.99 | 31.54 | -0.44 | [-1.46, +0.77] | 1.1117 | [-1.32, +0.56] | 62 / 75 / 943 (0.31) |

Beside the borrowed review-off margins: **h_SLU_M4b is 17.9 % wider** than B0r's 1.1218 and
**h_intent_M4b is 6.3 % wider** than B0r's 1.0051. The admitted five-contact review-on
configuration is therefore *noisier on the slot metric* than the two-contact review-off
configuration whose null cell B4b had to borrow, and measurably so. This is the single most
consequential number the cell produced, and it cuts against the arm: the first pass's margin was
slightly too narrow for the configuration it was applied to.

**Every metric's own-null interval contains zero.** The two realisations of one configuration are
statistically indistinguishable on all seven metrics; the -1.01 pp pooled-SLU point difference is
inside its own noise, and the sign tests on all four per-row metrics are nil (p from 0.31 to 1.00).

**Row-level agreement of the two passes.** 792 of 1,080 rows (**73.33 %**) deliver a byte-identical
answer; 56 rows (**5.19 %**) deliver a different (scenario, action) pair. For scale, B4b against the
anchor -- a real configuration change -- agrees on 755 rows and flips 65. Two realisations of the
same configuration therefore differ on about a quarter of rows, only slightly less than a genuine
single-factor change does. Greedy decoding at temperature 0 on a four-slot server is not
reproducible byte for byte, and this is the measurement of how far from reproducible it is.

Projection v3 and the TRAIN symmetric view both read the own null the same way: v3 -1.21 [-2.60,
+0.31], symmetric -1.16 [-2.52, +0.37].

## (c) B4b-rep minus the released direct anchor (secondary, never a gate)

Pooled SLU **+16.19 [+13.22, +19.17]**; intent +4.91 [+2.76, +7.09]; scenario +1.94 [-0.25, +4.29];
action +4.81 [+2.68, +7.11]; pooled span F1 +10.52 [+7.34, +13.88]; exact slot F1 row mean +9.42
[+7.36, +11.65]; row SLU-F1 +15.48 [+13.48, +17.68]. Saves / harms: intent 122 / 69 (p = 1.5e-4),
row SLU-F1 314 / 68 (p = 6.9e-39). The system-over-direct margin reads **+16.19** here against the
first pass's +17.20 and the anchor's own +14.65. Under projection v3 the same contrast is +18.53
[+15.40, +21.64] and under the TRAIN symmetric scorer +18.65 [+15.57, +21.76].

**Two scenarios lose intent beyond the band on this contrast and both reach owner decision 17's
flag**: `general` (-13.33 pp, CI95 [-24.07, -1.89], net harmed +8) and `lists` (-10.00 pp, CI95
[-17.86, -1.79], net harmed +6). This is a property of the system-versus-direct comparison and not
of module M4b; it gates nothing here and is recorded because the mandatory table asks for it.

## The rule, applied unchanged

| Clause | Requirement | Value | Margin | Passes |
| --- | --- | ---: | ---: | --- |
| 1(a), pooled SLU gain | CI95 lower bound of (R - anchor) > 0 | **+0.2992** | 0 | **YES** |
| 1(b), intent non-inferiority | CI95 lower bound > -1.0051 | **-0.6228** | -1.0051 | **YES** |
| 1(c), projection v3 agreement | v3 pooled SLU delta agrees in sign | **+0.8463** vs +1.5403 | same sign | **YES** |
| 2, own null | CI95 half-widths of (R - B4b) -- OUTPUTS | h_SLU_M4b **1.3222**, h_intent_M4b **1.0682** | -- | reported |
| 3, consequence | on REPLICATED the M4b provisional obligation is MET | see below | -- | fires |
| 4, mandatory tables | 18-scenario tables, both weightings, net harmed per scenario | delivered | -- | done |
| 5, symmetric scorer | reported beside every official number, never a gate | +1.02 (R - anchor), -1.16 (R - B4b) | -- | reported |

**Status REPLICATED and ADMITTED.** Read exactly once, from the single official score of the
complete merged manifest; no repeat, no re-score, no row filtering, and no third pass is registered
or authorized.

Cell B4b's own three HARMFUL triggers, recomputed on this pass and reported rather than gated: the
pooled SLU CI95 upper bound is +2.93, far above -1.1218; the intent CI95 lower bound is -0.62, above
-1.0051; and no scenario's intent CI95 upper bound is below zero. **None fires.**

Three honesty notes the program should carry forward.

1. **Clause 1(a) passes with much less room than the first pass had.** The CI95 lower bound is
   +0.2992 against the first pass's +1.1294. The point estimate +1.5403 clears the newly measured
   h_SLU_M4b of 1.3222 -- but only by 0.22 pp, where the first pass cleared its borrowed 1.1218 by
   1.43 pp. The module's effect on this roster is real and repeated in direction; its size is not
   pinned to better than about a point.
2. **Cell B4b's clause 4 is reported here, not gated**, exactly as the preregistration's section 6
   note 2 scoped it. It passes anyway on both M4b contrasts: 0 of 18 scenarios breach the band on
   (R - anchor) and 0 of 18 on (R - B4b), and no scenario reaches owner decision 17's five-net-harmed
   flag on either.
3. **`scenario` accuracy turned slightly negative** on this pass (-0.19 against the first pass's
   +0.28), well inside its own 0.90 pp null. Neither sign is a claim.

## Every scenario, (a) B4b-rep minus the sealed anchor (natural mixture; equal-scenario mean last)

| Scenario | n | Anchor SLU | B4b-rep SLU | Delta | Anchor intent | B4b-rep intent | Delta | Intent CI95 | Net harmed | Decision-17 flag | Beyond band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | --- |
| alarm | 60 | 52.66 | 63.63 | **+10.96** | 83.33 | 90.00 | +6.67 | [+1.39, +14.71] | -4 | no | no |
| audio | 60 | 47.75 | 56.99 | **+9.23** | 76.67 | 78.33 | +1.67 | [+0.00, +8.57] | -1 | no | no |
| calendar | 60 | 48.38 | 51.19 | +2.81 | 75.00 | 75.00 | 0.00 | [-6.15, +7.14] | 0 | no | no |
| cooking | 60 | 62.47 | 61.78 | -0.69 | 85.00 | 83.33 | -1.67 | [-5.77, +0.00] | +1 | no | no |
| datetime | 60 | 59.52 | 63.30 | +3.78 | 83.33 | 86.67 | +3.33 | [+0.00, +8.33] | -2 | no | no |
| email | 60 | 36.64 | 44.90 | **+8.26** | 85.00 | 86.67 | +1.67 | [-3.85, +7.55] | -1 | no | no |
| general | 60 | 15.45 | 10.71 | **-4.74** | 36.67 | 33.33 | -3.33 | [-12.31, +4.29] | +2 | no | no |
| iot | 60 | 55.53 | 61.22 | +5.68 | 86.67 | 88.33 | +1.67 | [+0.00, +5.36] | -1 | no | no |
| lists | 60 | 43.55 | 40.11 | -3.44 | 83.33 | 80.00 | -3.33 | [-8.06, +0.00] | +2 | no | no |
| music | 60 | 34.53 | 32.14 | -2.40 | 76.67 | 76.67 | 0.00 | [-6.90, +6.56] | 0 | no | no |
| news | 60 | 44.24 | 43.26 | -0.98 | 80.00 | 80.00 | 0.00 | [+0.00, +0.00] | 0 | no | no |
| play | 60 | 46.82 | 43.37 | -3.46 | 58.33 | 65.00 | +6.67 | [-1.92, +16.39] | -4 | no | no |
| qa | 60 | 57.04 | 57.06 | +0.02 | 75.00 | 75.00 | 0.00 | [+0.00, +0.00] | 0 | no | no |
| recommendation | 60 | 49.75 | 52.64 | +2.90 | 90.00 | 88.33 | -1.67 | [-7.55, +3.51] | +1 | no | no |
| social | 60 | 34.74 | 38.97 | +4.23 | 66.67 | 66.67 | 0.00 | [+0.00, +0.00] | 0 | no | no |
| takeaway | 60 | 48.84 | 45.96 | -2.88 | 85.00 | 81.67 | -3.33 | [-7.69, +0.00] | +2 | no | no |
| transport | 60 | 51.34 | 52.20 | +0.86 | 86.67 | 86.67 | 0.00 | [+0.00, +0.00] | 0 | no | no |
| weather | 60 | 53.81 | 53.96 | +0.15 | 90.00 | 93.33 | +3.33 | [+0.00, +8.62] | -2 | no | no |
| **equal-scenario mean** | 18 | | | **+1.68** | | | **+0.65** | | | | |

Eleven scenarios up and seven down on pooled SLU. The equal-scenario weighting (+1.68) sits slightly
*above* the natural mixture (+1.54), so the gain is not a single-stratum artifact. `alarm` is again
the largest winner (+10.96 here, +13.10 in the first pass) and `general` again loses on both
readings; `audio` and `email`, which were nil and +4.56 in the first pass, are +9.23 and +8.26 here,
while `lists`, the first pass's worst stratum at -5.74, is -3.44. Stratum-level movements of this
size between two realisations of one configuration are exactly what the own null measures, and none
of them is a claim.

## Every scenario, (b) B4b-rep minus cell B4b -- the own null by stratum

| Scenario | n | B4b SLU | B4b-rep SLU | Delta | B4b intent | B4b-rep intent | Delta | Intent CI95 | Net harmed | Decision-17 flag | Beyond band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | --- |
| alarm | 60 | 65.76 | 63.63 | -2.14 | 88.33 | 90.00 | +1.67 | [+0.00, +6.52] | -1 | no | no |
| audio | 60 | 47.32 | 56.99 | **+9.67** | 78.33 | 78.33 | 0.00 | [+0.00, +0.00] | 0 | no | no |
| calendar | 60 | 52.06 | 51.19 | -0.87 | 75.00 | 75.00 | 0.00 | [-4.62, +5.17] | 0 | no | no |
| cooking | 60 | 61.76 | 61.78 | +0.02 | 86.67 | 83.33 | -3.33 | [-9.86, +3.08] | +2 | no | no |
| datetime | 60 | 64.31 | 63.30 | -1.01 | 88.33 | 86.67 | -1.67 | [-5.66, +0.00] | +1 | no | no |
| email | 60 | 41.19 | 44.90 | +3.70 | 86.67 | 86.67 | 0.00 | [-5.08, +4.69] | 0 | no | no |
| general | 60 | 12.50 | 10.71 | -1.79 | 31.67 | 33.33 | +1.67 | [-3.92, +7.02] | -1 | no | no |
| iot | 60 | 59.02 | 61.22 | +2.20 | 85.00 | 88.33 | +3.33 | [+0.00, +8.33] | -2 | no | no |
| lists | 60 | 37.81 | 40.11 | +2.30 | 83.33 | 80.00 | -3.33 | [-8.06, +0.00] | +2 | no | no |
| music | 60 | 36.07 | 32.14 | -3.94 | 78.33 | 76.67 | -1.67 | [-5.56, +0.00] | +1 | no | no |
| news | 60 | 48.90 | 43.26 | **-5.64** | 80.00 | 80.00 | 0.00 | [+0.00, +0.00] | 0 | no | no |
| play | 60 | 50.85 | 43.37 | **-7.49** | 63.33 | 65.00 | +1.67 | [-6.67, +10.91] | -1 | no | no |
| qa | 60 | 54.98 | 57.06 | +2.07 | 73.33 | 75.00 | +1.67 | [+0.00, +5.56] | -1 | no | no |
| recommendation | 60 | 51.12 | 52.64 | +1.53 | 85.00 | 88.33 | +3.33 | [-3.17, +10.17] | -2 | no | no |
| social | 60 | 40.65 | 38.97 | -1.68 | 66.67 | 66.67 | 0.00 | [+0.00, +0.00] | 0 | no | no |
| takeaway | 60 | 49.14 | 45.96 | -3.18 | 83.33 | 81.67 | -1.67 | [-5.08, +0.00] | +1 | no | no |
| transport | 60 | 52.14 | 52.20 | +0.06 | 86.67 | 86.67 | 0.00 | [+0.00, +0.00] | 0 | no | no |
| weather | 60 | 55.51 | 53.96 | -1.55 | 93.33 | 93.33 | 0.00 | [+0.00, +0.00] | 0 | no | no |
| **equal-scenario mean** | 18 | | | **-0.43** | | | **+0.09** | | | | |

This is the table the program should look at before it trusts any 60-row stratum again. Changing
nothing at all moves `audio` by **+9.67 pp** and `play` by **-7.49 pp** of pooled SLU. Per-stratum
SLU movements of that size carry no information in this harness at this roster size.

## Projection v3 and the TRAIN symmetric view, beside the rule

| Arm | v3 SLU | v3 intent | v3 scenario | v3 action | v3 span F1 | Labels / fillers changed | Symmetric SLU | Symmetric span F1 |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| anchor | 51.99 | 79.35 | 85.46 | 80.65 | 40.30 | 20 / 195 | 52.09 | 41.38 |
| B4b | 54.05 | 79.72 | 85.93 | 80.83 | 41.85 | 21 / 170 | 54.26 | 43.99 |
| **B4b-rep** | **52.84** | **79.44** | **85.46** | **80.74** | **40.51** | 17 / 165 | **53.10** | **42.66** |
| direct | 34.31 | 75.37 | 84.17 | 75.93 | 23.24 | 47 / 36 | 34.46 | 24.38 |

| Contrast | v3 SLU delta | v3 CI95 | symmetric SLU delta | symmetric CI95 |
| --- | ---: | --- | ---: | --- |
| B4b - anchor (STOP) | +2.06 | [+0.53, +3.51] | +2.17 | [+0.62, +3.68] |
| **B4b-rep - anchor** | **+0.85** | [-0.53, +2.36] | **+1.02** | [-0.43, +2.59] |
| **B4b-rep - B4b** | **-1.21** | [-2.60, +0.31] | **-1.16** | [-2.52, +0.37] |
| B4b-rep - direct | +18.53 | [+15.40, +21.64] | +18.65 | [+15.57, +21.76] |

Clause 1(c) asks only for sign agreement and gets it: v3 +0.85 beside the unprojected +1.54. But
both post-processed views lose the interval that the unprojected number keeps -- v3's CI95 runs
[-0.53, +2.36] and the symmetric view's [-0.43, +2.59], each containing zero. The registered
decision number is the official unprojected one (owner decision 23), and that number's CI95 lower
bound is +0.30, so the clause passes as written; the two agreement views are consistent in direction
and weaker in strength, and this verdict records that rather than rounding it away. The replicate
needs *less* projection repair than either the anchor or the first pass (17 labels and 165 fillers
changed, against 20/195 and 21/170), which is the same direction the first pass reported.

## The kept-versus-flown diagnostic (reported; gates nothing)

The coordinator ordered this table. It is a **diagnostic and never a gate**, and no sub-population
claim follows from it: the resume note of 2026-09-18, section 10, forbids a kept-versus-flown claim
precisely because which rows the predecessor happened to finish is an arrival-order fact, and this
verdict honours that by keeping the split out of every clause.

**The split is strongly scenario-confounded, and that dominates everything below.** Sample ids are
flown in roster order and the roster is scenario-blocked, so the kept 580 rows hold all 60 rows of
`alarm`, `audio`, `datetime`, `iot`, `music` and `weather` and none of `email`, `lists`, `qa`,
`social` or `transport`, while the flown 500 hold all 60 of those five and none of the first six.
Kept: 580 rows, 119 speakers, 287 headset / 293 far-field. Flown: 500 rows, 105 speakers, 236 / 264.
A kept-versus-flown difference is therefore first a scenario-composition difference and only second
anything about batch composition.

| Metric | Kept 580 delta | Kept CI95 | Flown 500 delta | Flown CI95 | All 1,080 | Kept minus flown | Its CI95 | Visible at CI95 |
| --- | ---: | --- | ---: | --- | ---: | ---: | --- | --- |
| Official pooled SLU-F1 | **-2.03** | [-3.65, -0.39] | +0.06 | [-1.94, +2.23] | -1.01 | -2.08 | [-4.78, +0.59] | **no** |
| Pooled span F1 | -1.96 | [-4.80, +0.92] | +0.42 | [-2.26, +3.22] | -0.78 | -2.38 | [-6.64, +1.93] | no |
| Intent (scenario+action) | +0.34 | [-0.69, +1.46] | -0.20 | [-1.77, +1.30] | +0.09 | +0.54 | [-0.94, +2.14] | no |
| Scenario | 0.00 | [-0.97, +0.90] | -1.00 | [-2.46, +0.48] | -0.46 | +1.00 | [-0.70, +2.69] | no |
| Action | +0.69 | [-0.35, +1.79] | -0.20 | [-1.77, +1.30] | +0.28 | +0.89 | [-0.68, +2.57] | no |
| Exact slot F1 (row mean) | -0.99 | [-2.75, +0.88] | +0.10 | [-2.00, +2.28] | -0.48 | -1.09 | [-4.11, +2.01] | no |
| SLU-F1 (row mean) | -1.15 | [-2.44, +0.18] | +0.37 | [-1.59, +2.48] | -0.44 | -1.52 | [-4.06, +1.03] | no |

**No metric shows a difference between the two subsets that is visible at CI95.** The
kept-minus-flown difference on the primary metric is -2.08 pp with a CI95 of [-4.78, +0.59], which
contains zero. One subset-level interval does exclude zero -- the kept rows' own pooled SLU delta,
-2.03 [-3.65, -0.39] -- but that is a statement about six particular scenarios (the ones the
predecessor happened to reach), not about the resume, and its flown counterpart is a dead level at
+0.06.

Row-level agreement splits the same way and is worth one line: the kept rows agree with cell B4b on
**77.93 %** of delivered answers and flip intent on 3.97 %, the flown rows on **68.0 %** and 6.60 %.
That ordering is in the expected direction -- the flown rows were drawn under a genuinely new server
process and a new batch composition, the kept rows under the original one -- but it is confounded
with scenario in exactly the same way, and it gates nothing.

## The M4b slot diagnostics (cell B4b's own instrument)

Computed with the official scorer's own matching, reconstructed from each arm's sealed outputs.
Every row's reconstruction was checked against that row's sealed official `slu_f1` word and
character counts before any table was built, and the per-type decomposition closes on each arm's
official aggregate to 1e-6. Two reproductions license the columns: the A3 audit's anchor baseline
reproduces exactly, and **cell B4b's own first-pass slot table reproduces exactly** from its sealed
bytes. The three columns are the same instrument.

| Type | Rows with gold | Omits entirely (anchor -> B4b -> B4b-rep) | All exact | Exact mentions (of gold) | Spurious |
| --- | ---: | --- | --- | --- | --- |
| date | 135 | 81 -> 77 -> **76** | 26 -> 31 -> **35** | 28 -> 33 -> **37** of 138 | 7 -> 3 -> 6 |
| time | 72 | 19 -> 13 -> **13** | 7 -> 20 -> 13 | 8 -> 22 -> **14** of 76 | 11 -> 12 -> 8 |
| media_type | 57 | 38 -> 29 -> 34 | 8 -> 11 -> **13** | 8 -> 11 -> **13** of 57 | 8 -> 8 -> 13 |
| transport_type | 36 | 25 -> 24 -> 24 | 10 -> 11 -> 11 | 10 -> 11 -> 11 of 36 | 2 -> 1 -> 1 |
| business_type | 29 | 22 -> 22 -> **18** | 2 -> 3 -> **4** | 2 -> 3 -> **4** of 29 | 7 -> 8 -> 4 |
| order_type | 22 | 19 -> 16 -> 18 | 1 -> 3 -> 2 | 1 -> 3 -> 2 of 23 | 7 -> 8 -> 6 |
| relation | 15 | 15 -> 13 -> **12** | 0 -> 2 -> 2 | 0 -> 2 -> 2 of 16 | 0 -> 0 -> 1 |
| event_name | 41 | 22 -> 20 -> 20 | 10 -> 10 -> 9 | 10 -> 10 -> 9 of 41 | 13 -> 13 -> 14 |

Official SLU-F1 mass by type (word and character blocks summed; the last column is the
filler-distance, i.e. surface, mass of the matched spans):

| Type | FN mass (anchor -> B4b -> B4b-rep) | FP mass | TP | Filler-distance mass |
| --- | --- | --- | --- | --- |
| time | 116.34 -> 83.48 -> **90.12** | 96.34 -> 77.48 -> **74.12** | 110 -> 122 -> 120 | 74.34 -> 53.48 -> 58.12 |
| date | 203.58 -> 193.42 -> **187.89** | 49.58 -> 39.42 -> 41.89 | 108 -> 116 -> **118** | 35.58 -> 33.42 -> **29.89** |
| media_type | 95.30 -> 85.82 -> **83.93** | 35.30 -> 43.82 -> 41.93 | 38 -> 56 -> 46 | 19.30 -> 27.82 -> **15.93** |
| business_type | 49.47 -> 48.02 -> **45.32** | 19.47 -> 20.02 -> **17.32** | 14 -> 14 -> **22** | 5.47 -> 4.02 -> 9.32 |
| order_type | 44.12 -> 39.99 -> 42.12 | 18.12 -> 21.99 -> **16.12** | 6 -> 12 -> 8 | 4.12 -> 5.99 -> 4.12 |
| relation | 32.00 -> 28.00 -> **27.00** | 0.00 -> 0.00 -> 3.00 | 0 -> 4 -> **6** | 0.00 -> 0.00 -> 1.00 |
| transport_type | 51.75 -> 49.75 -> 49.75 | 5.75 -> 3.75 -> 3.75 | 22 -> 24 -> 24 | 1.75 -> 1.75 -> 1.75 |
| event_name | 57.58 -> 56.91 -> 60.05 | 39.58 -> 42.91 -> 48.05 | 38 -> 42 -> 42 | 13.58 -> 16.91 -> 20.05 |

**The mechanism replicates in direction on seven of the eight revised types** and its two registered
questions are answered the same way twice:

- **Date omission fell again and further**: 81 -> 77 -> **76** omitting rows, exact date mentions
  28 -> 33 -> **37** of 138, FN mass down 15.69 against the anchor (the first pass's -10.16), and
  the date filler-distance mass down 35.58 -> **29.89** (the first pass reached 33.42). On dates,
  the replicate is *better* than the first pass.
- **Time representation loss fell again, but by less**: omitting rows 19 -> 13 -> 13 (the first
  pass's whole gain, held), FN mass -26.22 against the anchor (the first pass's -32.86), and
  filler-distance mass 74.34 -> **58.12** (the first pass reached 53.48). Exact time mentions went
  8 -> 22 in the first pass and 8 -> **14** here: the biggest single-cell difference between the two
  realisations, and the main reason the pooled gain is +1.54 rather than +2.55.
- `business_type`, which did not move at all in the first pass (22 omitting rows, unchanged), moved
  here: 22 -> **18** omits and TP 14 -> **22**. `relation`, which moved off zero in the first pass,
  moved further (15 -> 12 omits, 0 -> 6 TP). `event_name` is the one revised type that is worse than
  the anchor on both passes' FN mass in this pass (57.58 -> 60.05).

Roster totals, all types: gold mentions 941 (fixed); predicted mentions 910 -> 923 -> **925**; exact
mentions 272 -> 302 -> **295**; omitted mentions 393 -> 369 -> **380**; spurious mentions 362 -> 351
-> **364**; filler-distance mass **814.46 -> 750.76 -> 749.37**. The surface gain replicates almost
exactly: -63.70 in the first pass, **-65.09** here.

**One convention note.** The first-pass verdict's per-type filler-distance column is the sum of the
word and character distance blocks, while its roster-total line is twice that sum. Both conventions
are reproduced here as that verdict used them, so the per-type columns above and the roster total
are each comparable with their own first-pass counterparts, but they are not comparable with each
other. `m4b-slot-diagnostics.json` carries both quantities explicitly.

As in the first pass, types outside the revised set moved too, and as in the first pass they are
recorded and not attributed.

## Cost and duty cycle

| Figure | B4b-rep (this attempt) | B4b-rep (run-cumulative) | B4b | Anchor | Direct | Registered ceiling |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Generation contacts | 2,501 | **5,423** | 5,407 | 5,417 | 1,080 | 11,880 (run-cumulative) |
| Contacts per row | 5.002 (of 500 flown) | 5.021 (of 1,080) | 5.006 | 5.016 | 1.00 | 11 |
| Repeated speech seconds | 7,592.04 | **15,487.59** | 15,432.81 | 15,459.76 | 3,084.53 | 33,930 |
| Prompt / completion tokens | 22,957,769 / 119,835 | -- | 47,187,487 / 254,335 | 45,998,267 / 255,153 | 2,459,915 / 26,764 | -- |
| Native task-contract tool calls | 495 | -- | 1,075 | 1,082 | 0 | 6,480 |
| FIT receipts / endpoints | 2,501 / 10,004 | 5,423 / **21,692** | 5,407 / 21,628 | -- | -- | -- / 47,520 |
| GPU hours (monitor active seconds) | **1.7430** (6,274.7 s) | -- | 3.4651 (12,474.3) | 3.3880 | 0.0871 | 12.0 |
| Generation wall seconds | 6,394.7 | -- | 12,796.8 | not in its receipts | 450.6 | -- |
| Slot occupancy; utilisation; parked | 0.881; 90.08 %; 0.018 | -- | 0.925; 92.43 %; 0.025 | --; 88.73 %; 0.022 | 0.658; 55.66 %; 0.281 | -- |
| Mean latency (s); preprocess (s, workers) | 9.006; 13.69 at 8 | -- | 8.760; 13.68 at 8 | -- | 1.098; 13.03 | -- |
| Official scoring jobs (seconds) | 1 (162.67) | 1 | 1 (387.22) | -- | -- | 1 |

The three attempts of this run id spent 2,922 (ABORTED, server death), 0 (ABORTED at preflight,
zero contacts) and 2,501 (FINALIZED) contacts. Run-cumulative exposure is **5,423 calls and
15,487.59 repeated speech seconds** against the unchanged 11,880-call ceiling -- **6,457 calls of
headroom** -- and every other ceiling held with room: 45.6 % of the FIT-endpoint ceiling and 45.6 %
of the speech ceiling, both run-cumulative. Native task-contract calls are **495 on this attempt**,
7.6 % of the 6,480 ceiling; the ABORTED predecessor sealed no generation manifest, so its tool-call
count is not in its receipts and no run-cumulative tool-call figure is quoted here. Its contacts and
speech seconds, which the exposure gate actually holds, are on its attempt record and are included
above.

**What the resume bought.** A full re-fly of this cell would have cost about what cell B4b's own
measured pass cost, **3.4651 GPU hours**; this attempt cost **1.7430**, so the resume saved
**1.7221 GPU hours** of serving-monitor active time (the resume registration's ex-ante estimate was
about 1.9; the measured saving is 1.72 because the resume realised 2,501 contacts against its
predicted ~2,500 at a slightly lower occupancy than the first pass). **2,922 contacts never had to
be paid a second time.** The only contacts the resume paid twice are the four INCOMPLETE rows'
predecessor contacts.

**Duty cycle.** Slot occupancy 0.881 over four serving slots, monitor utilisation 90.08 %, parked
fraction 0.018, mean latency 9.006 s, 0.391 contacts per second, mean power 92.4 W. Against the
first pass's 0.925 / 92.43 % / 0.025 at 8.760 s, the resumed flight ran marginally cooler and
slightly slower per contact -- consistent with a 500-row flight's shorter ramp, and with nothing
else this read can name.

**Prompt fit.** `every_request_fits = true` on all 2,501 receipts of this attempt and all 2,922 of
its predecessor. Minimum margin **8,782 tokens** in the `reviewer` phase this attempt (8,424 across
both attempts), widest realised request 15,794 tokens (16,152 across both), against the
24,576-token slot -- below the first pass's widest 16,334 and its 8,242-token minimum margin. The
per-phase maxima are perception 4,270, solver 13,914, planner 15,772, reviewer 15,794.

## What is not claimed

- **No new claim about module M4b's effect size.** This cell re-applies cell B4b's own clauses to a
  second realisation and measures the configuration's own noise. It does not enlarge, re-estimate,
  average or replace the first pass's numbers, and the first verdict stands unchanged beside this
  one. The honest summary of two passes is "a pooled-SLU gain of between about one and two and a
  half points on this roster", not either single figure.
- **No superiority, generalization, paper-scale or held-out claim.** TRAIN Fold A is an exposed
  discovery roster; nothing is said about Fold B, DEV-1000 or the test split, which stay unread.
- **No intent, scenario or action gain.** All three sit inside the own null on both passes.
- **No component-causal attribution below the store.** Eight cards moved together in one release;
  neither pass can say which card, or which sentence of a card, paid.
- **This cell measures its own noise, not a general one.** `h_SLU_M4b = 1.3222` and
  `h_intent_M4b = 1.0682` belong to this configuration, this roster and this serving geometry. They
  must not be imported into another cell the way the DEV-1000 half-widths once were, and they must
  not be read as a replacement for B0r's review-off null in cells that run review-off.
- **No sub-population claim from the kept/flown split**, which is scenario-confounded by
  construction and gates nothing.
- **No claim that a resumed pass is a cleaner replicate than a re-flown one.** 580 rows keep the
  batch composition they were drawn under and 500 rows were drawn under a new one; the factor this
  cell measures is unchanged in kind, and no claim is made that it is unchanged in magnitude.
- **A REPLICATED verdict admits the v2 pins into the SLURP default plan; it does not admit them into
  a paper.** Stage-3 claims belong to a separately admitted paper repository.
- **Nothing about the review loop**, held identical to the anchor here.

## The harness-admission consequence (a proposal for the coordinator)

This verdict does not write `docs/receipts/harness-admission.json`; the receipt is the coordinator's
to close and `scripts/checks/harness_admission_check.py` is its oracle. Clause 3 of the
preregistration fires on REPLICATED, so the proposal is a **second entry beside the existing one**,
exactly as the KC-E1f v1/v2 pair does -- the first entry stays, unchanged.

**A. The existing M4b entry.** Its `provisional` block becomes:

- `state`: **MET**
- `met_by`: this verdict, `docs/results/2026-09-19-slurp-b4b-replicate-verdict.md`
- `note`: the requirement named two branches ("either a request-identical replicate of this cell
  (about 3.5 GPU hours) or the B5 / B5r combination pair"); owner decision 13 chose the first and
  this cell is it. The `not_admitted_for` line "any default plan before the replication obligation
  is met" is discharged, so **the SLURP default plan may now carry the `slot-contracts-v2` release
  `f8e42d4f...` and snapshot `d5992bd1...` pins**. Under the `stores` re-pin form, a default plan
  arms this module only by pinning exactly those two ON-arm bytes.

**B. The new replication entry.**

- **module**: date/time slot-contract revision (slot store v2) -- **replication**
- **carrier**: `slurp`
- **class** / **key** / **form** / **on** / **off**: identical to the first entry (`stores`,
  `knowledge_stores.slot-contracts`, `repin`, v2 release/snapshot ON, v1 release/snapshot OFF)
- **row**: `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-REPLICATE-V2`
- **status**: **ADMITTED**
- **status_basis**: all three registered replication clauses pass on the second realisation --
  official pooled SLU-F1 48.5336 -> 50.0740, +1.5403 pp CI95 [+0.2992, +2.9287], lower bound above
  zero; intent 77.9630 -> 78.6111, +0.6481 pp CI95 [-0.6228, +1.8734], lower bound above the
  -1.0051 margin; projection v3 +0.8463 agreeing in sign. The configuration's **own null is now
  measured**: h_SLU_M4b 1.3222 pp and h_intent_M4b 1.0682 pp at CI95, 17.9 % and 6.3 % wider than
  the review-off values the first pass borrowed. The mechanism replicates on its own instrument:
  date omissions 81 -> 76, exact date mentions 28 -> 37 of 138, time FN mass -26.22, roster
  filler-distance mass 814.46 -> 749.37 against the first pass's 750.76.
- **evidence**: this verdict; the sealed score
  `7e39a28d7f7bcb04c3012102dd9392e8c070f7b058f4e3452d7dbb01dbcc9481`; the run manifest
  `810ee83fa9e022dec7f9ce576cf0583e89efd411d4d0bbe549dfb82f5baa3a7e`; the paired read
  `SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-B4B-REPLICATE-PAIRED-ANALYSIS-V1/` with
  `score-contrasts.json` `a83d0ba163bde043d6e41cd0f2d8654a360365e032a8d2605554424b580b23cf` and
  every other output hashed in its `README.md`
- **caveats**: the pass clears clause 1(a) by 0.30 pp of CI95 lower bound against the first pass's
  1.13, and the point estimate clears the newly measured h_SLU_M4b by only 0.22 pp; the two passes
  agree on 73.3 % of delivered answers, so a third realisation would move the point estimate again;
  the arm was sealed as a resume-recovery, with 580 rows carrying the predecessor's bytes and 500
  flown after the server was replaced.
- **provisional**: `state` **MET** on registration -- a replication entry carries no further
  replication debt, and no third pass of this configuration is registered or authorized.

**One point the coordinator may wish to record while writing the row.** The first entry's
`margins_from` block names cell B0r's review-off null as the source of its margins. That block is
now superseded in substance for this module: the configuration has its own null, and it is wider.
The program should decide whether other SLURP cells that borrow 1.1218 while running the five-contact
review-on geometry should instead borrow 1.3222. This verdict does not decide it.

## Exposure

**Zero model contacts; the sealed bytes were copied, never opened for writing.** This read made no
model, tokenizer, encoder, ASR or server contact, and touched no serving session, flight worktree,
scheduled task or flight lock. The only scorer invocations are the model-free projection-v3 and
TRAIN symmetric scorings, four arms each, every one over a COPY of that arm's sealed `outputs.jsonl`
written under `SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-B4B-REPLICATE-PAIRED-ANALYSIS-V1/`. The
ABORTED predecessor attempt's trace was streamed read-only by the harness's own resume reader, and
only response *digests* were compared -- no delivered text, transcript, gold filler or utterance was
printed, stored or persisted anywhere by this read. No sealed file was opened for writing, moved or
renamed; no exposure-ledger row, harness-admission receipt, results ledger or readiness document was
edited. Execution profile `model-free-check`.

One documentation divergence, recorded rather than silently resolved: the preregistration's section
12 named the analysis directory
`analysis/SAEA-SLURP-B4B-REPLICATE-OWN-NULL-PAIRED-ANALYSIS-V1` and the verdict
`docs/results/2026-09-17-slurp-b4b-replication-v2-verdict.md`; the coordinator's read brief named
`analysis/SAEA-SLURP-B4B-REPLICATE-PAIRED-ANALYSIS-V1` and this file. The brief's names were used.
Nothing about the recipe's estimators, seed, draws, interval levels, contrasts, tables or decision
rule was changed by that choice.
