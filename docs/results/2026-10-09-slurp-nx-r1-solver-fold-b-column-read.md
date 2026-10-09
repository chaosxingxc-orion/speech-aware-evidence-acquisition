# NX round R1 iteration 1 (Solver instruction-template column, TRAIN Fold B): every arm NOT NOMINATED on the official column; r1-c3 empties rows (pooled +0.96 [-0.17, +2.09], per-row -2.22 [-3.27, -1.19]); the declared +1.80 arm r1-c1 is the worst (-0.73)

Read 2026-10-09 by Claude Opus 5.5 (analysis agent, on the coordinator's brief, Fable 5.1) in the worktree
`fable/nx-r1-results`. Model-free: this note opened no model, server, encoder, embedder, tokenizer or GPU, ran no
scorer and wrote nothing under the data root; it reads the on-file outputs of the registered read
`SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-COLUMN-READ-V1` and the sealed run. No utterance text, transcript, gold value,
slot filler or model output was printed or persisted; only counts, rates, deltas, ids and hashes appear below.

**DESCRIPTIVE.** Development numbers on a TRAIN construction fold (owner decisions 28 and 86), never a test claim and
never a system-level claim. The claim ceiling of the cell is `nominated`. The verdict words in section 5 apply the
iteration-2 nomination rule retroactively, as fixed by the coordinator in merge `f89c58b7e` (hand-off entry
2026-10-09T19:28:38Z); the registered iteration-1 rule (node-local raw primary, section 5 of the package README) is
quoted beside it.

## 0. Answer in five lines

1. No iteration-1 arm is NOMINATED: no official pooled SLU-F1 delta vs `lock` has a CI95 lower bound above 0, and every candidate also fails the intent guard (9 to 13 rows differ, limit 7); none is HARM on the pooled column.
2. `r1-c3` (explicit empty-entity decision) is the only arm above the `aa` twin at the point (+0.96 [-0.17, +2.09] vs twin +0.57), but its per-row SLU-F1 is a measured loss (-2.22 [-3.27, -1.19]): it removes false-positive mass (entity FP 484 -> 378) and also empties values that were right (entity TP 498 -> 473).
3. `r1-c1` (value-in-supply extraction, the declared +1.80 pp arm) is the worst arm officially (-0.73 [-1.65, +0.17]); false fill rises +7.91 pp; the hypothesis "extract the value that is printed in the supply" is refuted.
4. `r1-c5`'s raw node gain (+2.50 [+1.02, +4.07]) is formatting that the v3 delivery normaliser already repairs: normalised +1.30 [-0.19, +2.78], official -0.15 [-1.23, +0.89].
5. The declared round effect (+1.80 pp) was not met; the empty-entity decision is the lever, to be gated by owner rule 199 in iteration 2, which decides on the official column.

## 1. Identities

| item | value |
| --- | --- |
| cell / experiment | `slurp-native-stage3-nx-r1-solver-fold-b-v1` (package `docs/readiness/2026-10-09-slurp-nx-r1-solver-fold-b-v1/`) |
| run / attempt | `SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-V1` / `attempt-slurp-native-stage3-nx-r1-solver-fold-b-generation-v1` |
| flight commit | `09ce9eedee667d56aa1a7728819fa95288ecc0e2` (`study_commit` of the run manifest; manifest status COMPLETED) |
| roster | TRAIN Fold B `SLURP-EVO-FOLD-B-V2`, 1,080 rows (392 empty-gold, 688 non-empty-gold), split identity `4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a` |
| flight | arm opened 2026-10-09T15:20:10Z; 1,080 rows, 8,640 contacts (8 per row: Perception, then the seven Solver arms), 2 h 16 m 54 s; one official score job (373.6 s, rc 0) |
| run manifest | sha256 `cc4fb0bc6559324f695bcf3c07aa1034bd1af2d1e4cca99ff3a03fa7decb1af0` |
| outputs / scores | `44de26d91c7326a3098ae5ce3ea8bd9acf6445b4dea942a5d5d7d3f3b388284c` / `87f930270332755c1b9d70137dd6e3db4e00ca83d2de87f8a93fdbdcda7c9ff3` |
| raw trace / trace manifest | `b316798175e3e6a9eeafea21df652272e48b184c6bdc822a6a1f7178ecb5ef11` / `cc0aceeef685747fe85696f9646164a6597fd4120e2fcdfb3f3abfbec5f031fc` |
| protocol / composed config | `82c4f0a521eeb83e88b6dac0187ce2fb0e03514ffa95971cd50a75c76f1002ae` / `a31825ae0c0f8b03312911403c86cee3ee8f03420d2a5cf21860c6ea7284eae2` |
| READ run | `SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-COLUMN-READ-V1`, root countersigned after the seal (commit `93e863031`) |
| recipe | `slurp-nx-r1-solver-fold-b-column-analysis-v1`, `docs/readiness/2026-10-09-slurp-nx-r1-solver-fold-b-v1/analysis-recipe-v1.json` sha256 `7a4ac48450c601323817a5488826354fdac3d0847ae45ddc369a5a0ba32ef8b5` |
| read driver | `scripts/analysis/nx_r1_read.sh` (sha256 at this note's base `e0c1e7d8...`) |
| node-local v1 (registered, raw primary) | `node-local/report.json` `188f957cfcbe5de4d591f83e7500af1558eeb8b9ebba007b411ed5b6c1fb321c`, `tables.md` `84372035abc10909ef93948db812ef6e95180eabba07bdd340ef76501fb9a60a` |
| node-local v2 (re-read, normalised primary) | `node-local-v2/report.json` `b562b7c0b4d09bc1125b32ab079bc3b07fd8b21695de20f77a695e956be6149e`, `tables.md` `06757bf2be5adabf250b4c67f2185f7a539c1a9500a6e6c48c4df8c3e5970728`; schema `saea-nx-solver-column-read-v2`, primary `exact_set_normalised`, all 1,080 rows under `saea-deliver-normalise-v3` |
| official columns | `<run dir>/supply-variants/score-summary.json` `8a5de8acc39e46d1f7c65570a23c7c799a89638de83e3e704cf097cbbc3413c8` (seven column scorings, `slurp-slu-official-train`, never sharded) |
| paired contrasts (`score-contrasts.json`) | aa `c12572b9...`, c1 `f355ee56...`, c2 `ddd9ad2c...`, c3 `a6c0d84f...`, c4 `7ce44708...`, c5 `b956ecb8...`; driver `stage3_paired_read.py` `da9485fc...`; every `verdict.json` status DESCRIPTIVE |
| read contacts | model 0, encoder 0, tokenizer 0, GPU 0; scorer 7 (the seven local official column scorings) |

Paths: analysis root `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-COLUMN-READ-V1/`
(`node-local/`, `node-local-v2/`, `aa-vs-lock/`, `r1-c1-vs-lock/` .. `r1-c5-vs-lock/`); run dir
`$SPEECHRL_DATA_DIR/runs/SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-V1/attempt-slurp-native-stage3-nx-r1-solver-fold-b-generation-v1/`.

The arms (package README section 1): `r1-c1` value-in-supply extraction (declared +1.80 pp, the round's carrier),
`r1-c2` copy suppression with a heard-span requirement (+0.63), `r1-c3` explicit empty-entity decision under decision
199 (+0.89), `r1-c4` the ChatGPT donor ported onto the locked template (+0.6, author prior), `r1-c5` contract
tightening plus TRAIN-side filler conventions (+0.28); `aa` the in-chain twin (`replicate_of lock`); `lock` the
locked template, delivering, last. Base: the review-off COMP-1b module graph (agree-vote-seed + centroid-boundary-key),
no tool schema on any role, program `phase-native-module-v1-c8`.

**Smoke stops and recovery.** The four-row smoke `SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-SMOKE-4-V1` stopped three
times before the arm opened: attempt v1 made 32 contacts and failed at `runtime.seal()` on the template-variant
delivery validator (fixed on master `d2bc8f67e` / `6633c9251`); recovery rec1 was refused pre-contact (0 contacts) by
the run-cumulative plan budget (32 already spent on the run id); rec2 was refused pre-contact (0 contacts) by the FIT
gate because its `contact_cap` had been scaled to 256 instead of the structural 4 x 8 x 4 = 128. The coordinator ruled
both refusals registration defects of the single recovery, not flight failures, and amended it to rec3 (generation
budget 64 calls / 164 speech-seconds run-cumulative, FIT cap 128); rec3 passed at 15:20:00Z and the arm opened ten
seconds later with its attempt id and budgets unchanged. All three spent smoke attempt ids are preserved unread.

## 2. The official column (decides; paired row bootstrap vs `lock`, cluster `sample_id`, 10,000 draws, seed 20260915)

`lock` levels: pooled official SLU-F1 62.13 %, per-row mean SLU-F1 41.68 %, intent 82.22 %.

| arm | pooled SLU-F1 % | pooled delta pp [CI95] | per-row SLU-F1 delta pp [CI95] (saves / harms) | intent % | intent delta pp [CI95] (rows differing) | headset per-row delta pp (s / h) | far-field per-row delta pp (s / h) |
| --- | ---: | --- | --- | ---: | --- | --- | --- |
| `aa` twin (bar) | 62.70 | **+0.57 [-0.10, +1.27]** | +0.38 [+0.03, +0.78] (19 / 12) | 82.41 | +0.19 [+0.00, +0.46] (2) | +0.56 (11 / 5) | +0.21 (8 / 7) |
| `r1-c1` | 61.40 | -0.73 [-1.65, +0.17] | +0.93 [+0.21, +1.69] (36 / 21) | 82.31 | +0.09 [-0.46, +0.65] (9) | +1.41 (22 / 10) | +0.47 (14 / 11) |
| `r1-c2` | 62.35 | +0.22 [-0.74, +1.16] | -0.05 [-0.84, +0.76] (38 / 32) | 82.59 | +0.37 [-0.19, +1.02] (10) | +0.15 (21 / 16) | -0.25 (17 / 16) |
| `r1-c3` | 63.09 | **+0.96 [-0.17, +2.09]** | **-2.22 [-3.27, -1.19]** (28 / 54) | 82.50 | +0.28 [-0.28, +0.83] (9) | -1.62 (15 / 23) | -2.80 (13 / 31) |
| `r1-c4` | 61.93 | -0.20 [-1.20, +0.79] | +0.09 [-0.71, +0.91] (42 / 34) | 82.13 | -0.09 [-0.74, +0.56] (13) | +0.10 (23 / 18) | +0.08 (19 / 16) |
| `r1-c5` | 61.98 | -0.15 [-1.23, +0.89] | -0.62 [-1.43, +0.19] (40 / 41) | 82.50 | +0.28 [-0.28, +0.83] (9) | -0.87 (19 / 24) | -0.38 (21 / 17) |

The c3 pooled CI95 prints as [-0.16, +2.09] at two decimals in the tables (lower bound -0.1647); quoted as
[-0.17, +2.09] in the brief and the answer lines, the same interval. Channel columns are per-row SLU-F1 deltas
(headset n = 527, far-field n = 553); the tool emits per-channel numbers for per-row metrics only.

Equal-scenario weighting (18 scenarios x 60 rows, unweighted mean of per-scenario deltas, stratified bootstrap),
reported beside the natural mixture and never gating: aa +0.67 [-0.04, +1.46]; c1 -0.93 [-1.94, +0.11]; c2 +0.11
[-0.83, +1.10]; **c3 +1.96 [+0.42, +3.55]** (12 scenarios up, 6 down); c4 -0.21 [-1.24, +0.80]; c5 +0.15 [-0.86, +1.15].

Official entity counts (exact spans, `entities` row of the official script): lock TP / FP / FN 498 / 484 / 446;
aa 500 / 485 / 444; c1 512 / 534 / 432; c2 500 / 471 / 444; **c3 473 / 378 / 471**; c4 501 / 500 / 443; c5 498 / 463 / 446.

**Why pooled and per-row disagree.** The per-row SLU-F1 of an empty-gold row is 0 whatever the arm answers
(`_prf` in `reproduction/slurp_scoring.py`: with TP = 0 both precision and recall are 0, so an empty answer on an
empty-gold row scores the same 0 as a false fill). The per-row mean is therefore blind to the 392 empty-gold rows and
sees only non-empty-gold rows, while the pooled micro F1 counts every false positive. c3's per-row loss is its
non-empty loss; c3's pooled gain is the false-positive mass it removes. c1's per-row gain (+0.93, CI-LB > 0) is the
mirror image: 14 more exact entities on non-empty rows count, its +50 extra false positives on empty-gold rows do not.
The per-row column is not the rule's metric and must never be read as a gain on its own.

## 3. Node-local tables (E2 reader, paired vs `lock`, whole-utterance cluster bootstrap, 10,000 draws, seed 20260915, CI95)

Normalised = the arm's first Solver answer after the delivered row's own normaliser (`saea-deliver-normalise-v3`,
through `stage3_rollout_score.normalise_arm_answer`, the function the official column renderer calls): the PRIMARY
from iteration 2 on. Raw = the sealed first-visit text: the registered iteration-1 primary, now a diagnostic.

| arm | exact-set normalised pp [CI95] | exact-set raw pp [CI95] | empty-gold false fill pp [CI95] (n 392) | non-empty exact normalised pp [CI95] | non-empty exact raw pp [CI95] | screen normalised / raw |
| --- | --- | --- | --- | --- | --- | --- |
| `aa` | +0.19 [-0.65, +1.02] (11 / 9) | +0.00 [-0.74, +0.74] (9 / 9) | +0.26 [-1.28, +2.04] | +0.44 [-0.44, +1.31] | +0.15 [-0.58, +0.87] | twin |
| `r1-c1` | -1.67 [-3.15, -0.19] (24 / 42) | -1.85 [-3.43, -0.37] | **+7.91 [+5.10, +10.97]** (35 / 4) | +1.89 [+0.44, +3.34] | +1.60 [+0.15, +3.20] | fail / fail |
| `r1-c2` | +0.83 [-0.56, +2.22] (34 / 25) | +1.11 [-0.28, +2.59] | -1.79 [-4.59, +0.77] | +0.29 [-1.31, +1.89] | +0.73 [-1.02, +2.47] | fail / fail |
| `r1-c3` | **+4.63 [+2.87, +6.39]** (74 / 24) | +4.63 [+2.87, +6.48] | **-15.82 [-19.64, -12.24]** (2 / 64) | **-1.74 [-3.34, -0.15]** (10 / 22) | -1.74 [-3.34, -0.15] | fail (secondary) / fail (secondary) |
| `r1-c4` | -0.65 [-2.13, +0.83] (30 / 37) | -0.19 [-1.76, +1.30] | +1.79 [-1.02, +4.85] | +0.00 [-1.60, +1.60] | +0.73 [-1.02, +2.47] | fail / fail |
| `r1-c5` | +1.30 [-0.19, +2.78] (41 / 27) | **+2.50 [+1.02, +4.07]** (50 / 23) | -3.06 [-6.12, +0.00] (12 / 24) | +0.29 [-1.31, +1.89] (17 / 15) | +2.18 [+0.44, +3.92] (26 / 11) | fail / **pass** |

Parentheses: discordant rows (arm only / `lock` only). Empty-gold false fill is unchanged by the normaliser for every
arm. Marginal levels (normalised; raw in brackets): exact-set lock 49.81 [48.70], aa 50.00 [48.70], c1 48.15 [46.85],
c2 50.65 [49.81], c3 54.44 [53.33], c4 49.17 [48.52], c5 51.11 [51.20]; false fill lock 34.44, c3 18.62, c1 42.35;
parse validity 99.72 (lock) to 100.00; predicted items lock 982, c1 1,046, c3 851, c5 961.

Raw vs normalised flips (rows whose exact-set changes under the v3 normaliser; no parse flips in any arm):

| arm | text changed | raw false -> normalised true | raw true -> normalised false | net |
| --- | ---: | ---: | ---: | ---: |
| `lock` | 101 | 16 | 4 | +12 |
| `aa` | 104 | 18 | 4 | +14 |
| `r1-c1` | 111 | 18 | 4 | +14 |
| `r1-c2` | 103 | 12 | 3 | +9 |
| `r1-c3` | 98 | 16 | 4 | +12 |
| `r1-c4` | 88 | 11 | 4 | +7 |
| `r1-c5` | 65 | **3** | 4 | **-1** |

This table is the c5 story in one line: the normaliser repairs 12 net `lock` rows and -1 net c5 row, so c5's raw
advantage of 27 rows (+2.50 pp) shrinks to 14 rows (+1.30 pp) once both sides are compared as delivered; c5's
template does by instruction what the delivered row's normaliser already does by rule.

## 4. Per slot type and per scenario: where c3 and c5 acted

Node-local per-slot-type totals (normalised; 944 gold entities on the roster):

| arm | gold exact | gold missing | gold wrong | predicted | spurious |
| --- | ---: | ---: | ---: | ---: | ---: |
| `lock` | 498 | 202 | 244 | 982 | 240 |
| `r1-c3` | 473 | 251 | 220 | 851 | 158 |
| `r1-c5` | 498 | 216 | 230 | 961 | 233 |
| `r1-c1` | 512 | 190 | 242 | 1,046 | 292 |

**r1-c3 (the empty decision).** It predicts 131 fewer entities: spurious -82 and wrong -24 (FP mass removed), but
missing +49 and exact -25 (values that were right are now absent). Exact losses concentrate on short, operation-adjacent
types: `date` -8 exact / +11 missing, `media_type` -3 / +7, `transport_type` -3 / +3, `weather_descriptor` -3 / +2,
`event_name` -2 / +4, `food_type` -2 / +2. The spurious cuts are spread over `device_type` -10, `food_type` -7,
`list_name` -6, `media_type` -5, `place_name` -5, `house_place` -4; no type gains a spurious entity beyond +2
(`ingredient`). Per scenario (official pooled SLU-F1 within 60 rows; descriptive, wide intervals): gains in `audio`
+12.34, `music` +7.08 [+2.3, +14.6], `alarm` +6.61 [+0.2, +13.4], `qa` +5.75 [+0.7, +12.3], `recommendation` +5.28
[+1.1, +10.4]; losses in `weather` -3.45 [-7.6, -0.1], `takeaway` -2.53, `calendar` -2.41, `transport` -2.33, `social`
-1.41 (12 scenarios up, 6 down). The losing scenarios are the ones whose slot types carry the exact losses above
(dates, weather descriptors, transport types); this note did not split the per-scenario empty-gold share, so where the
gains come from is stated only as the aggregate FP removal of section 2.

**r1-c5 (contract and filler conventions).** Gold exact is unchanged in total (498 = 498): `food_type` +3, `relation`
+2, `news_topic` +2, `time` +2 against `date` -3, `media_type` -2, `device_type` -2; spurious 240 -> 233. The
conventions moved filler surface forms, most of which the v3 normaliser already maps (section 3). Officially c5 removes
21 exact-span FPs (484 -> 463) but loses distance-credit TP mass (official SLU-F1 TP 1,352 -> 1,340, FN 786 -> 805),
net -0.15 pp. Per scenario: `alarm` +5.74 [+1.3, +11.2], `audio` +4.48 [+0.9, +10.0], `cooking` +3.48 [+0.4, +7.1]
against `general` -4.08, `lists` -4.04 [-7.5, -1.2], `calendar` -3.10, `news` -2.46; 9 scenarios up, 9 down.

**r1-c1 (for completeness).** +64 predicted entities buy +14 exact and +52 spurious: a net emission precision of about
0.22 (14 / 64), below the break-even 0.318 that the package declared (section 2 of the package README); the harm end of
the declared range [-0.72, +1.80] is where the arm landed.

## 5. Verdict under the iteration-2 nomination rule (applied retroactively)

Rule (`docs/readiness/2026-10-09-slurp-nx-r1-i2-solver-fold-b-v1/README.md` section 5): NOMINATED iff (a) the official
pooled SLU-F1 delta vs `lock` has CI95 lower bound > 0, (b) the delta exceeds the `aa` twin's +0.57, and (c) the intent
guard holds (rows whose official intent correctness differs from `lock` <= 7); HARM iff the CI95 upper bound < 0.

| arm | (a) CI-LB > 0 | (b) delta > +0.57 | (c) intent rows <= 7 | HARM | verdict |
| --- | --- | --- | --- | --- | --- |
| `r1-c1` | no (-1.65) | no (-0.73) | no (9) | no (UB +0.17) | **NOT NOMINATED** |
| `r1-c2` | no (-0.74) | no (+0.22) | no (10) | no | **NOT NOMINATED** |
| `r1-c3` | no (-0.16) | yes (+0.96) | no (9) | no | **NOT NOMINATED** |
| `r1-c4` | no (-1.20) | no (-0.20) | no (13) | no | **NOT NOMINATED** |
| `r1-c5` | no (-1.23) | no (-0.15) | no (9) | no | **NOT NOMINATED** |

Under the registered iteration-1 rule (raw node-local exact-set CI-LB > 0, no secondary loss, intent guard, official
point delta above the twin bar) the outcome is the same: c5 passes the raw screen but its official delta (-0.15) is
below the twin bar and its intent guard fails; c3 fails the screen on its non-empty secondary.

What each verdict means:

- **r1-c3** is the only arm whose pooled delta is positive at the point and above the twin, while its per-row SLU-F1 is
  a measured loss (-2.22 [-3.27, -1.19]). It **empties rows**: on empty-gold rows it removes false-positive mass (false
  fill 34.4 % -> 18.6 %, official entity FP 484 -> 378), which the pooled F1 rewards; on non-empty-gold rows it also
  empties or truncates answers that had a correct value (non-empty exact -1.74 pp, official entity TP 498 -> 473,
  missing +49), which the per-row F1 sees in full. The net pooled gain is not resolved and the per-row loss is. The
  decision is the right lever applied with no gate: it fires on heard values as well as on absent ones.
- **r1-c1** is the worst arm officially. Its mechanism ("extract the value that is printed in the supply") raised false
  fill by +7.91 pp (35 rows vs 4) and spurious entities by +52 for +14 exact; the declared conversion (117 in-view
  MISSING values x 0.2471) did not occur at a usable precision. **The hypothesis is refuted** on this base; telling the
  Solver that supplied values exist makes it copy them.
- **r1-c5**'s raw gain (+2.50) is formatting that the v3 normaliser already repairs: normalised +1.30 [-0.19, +2.78],
  official -0.15 [-1.23, +0.89].
- **r1-c2** and **r1-c4** are null on every view.
- **The round's declared effect (+1.80 pp official pooled SLU-F1, carried by r1-c1) was not met**; the best measured arm
  is +0.96, below the 1.49 pp provisional floor and unresolved.

The `aa` twin sets the bar: pooled +0.57 [-0.10, +1.27], intent +0.19 (2 rows), node exact-set raw +0.00 (9 / 9). The
twin's per-row CI-LB (+0.03) is above 0, a reminder that a lone per-row CI-LB > 0 is within the in-flight null of this
instrument.

## 6. Lessons for the instrument and for iteration 2

1. **The node primary is post-normaliser.** A node-local metric must compare arms as delivered; the raw view rewarded c5
   for 13 rows of formatting the delivered row already gets for free (section 3). Adopted as reader schema v2 (merge
   `52b053fed`); raw stays a diagnostic.
2. **The official column decides.** Even the normalised node metric does not rank arms as the official column does
   (c3 normalised +4.63 vs official +0.96; c5 +1.30 vs -0.15), because exact-set per row ignores entity count per row
   and the official partial (word / char distance) credit. Adopted as the iteration-2 nomination rule (merge `f89c58b7e`).
3. **Per-row SLU-F1 is blind to empty-gold rows** (section 2). It must not be quoted as an effect for any mechanism
   that changes how often the Solver answers empty; pooled micro is the estimand.
4. **The empty-entity decision is the lever**, measured at -15.82 pp false fill, but ungated it drops heard short values.
   Owner rule 199 makes empty legal as a model decision; iteration 2 gates it on heard values so that nothing heard is
   deleted.
5. **The exchange rate over-predicts when the gain is formatting.** At +0.056 pp per raw-exact row
   (`docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md`), c5's raw +27 rows predicted about +1.5 pp; the
   official column read -0.15. For c3 the uniform rate predicts +2.8 pp from +50 rows, the class-split rates (62 net
   emptied false fills x 0.033, -12 non-empty rows x 0.056) about +1.4 pp, and the column reads +0.96 (arithmetic of
   this note from the on-file rates). Declared effects should use the class-split rates on the normalised view.
6. **Declared vs measured calibration was poor** (raw-exact rows: c1 declared +32 vs measured -20, c3 +35 gross vs +50,
   c5 +5 vs +27), which iteration 2 already answers by building its candidates from the measured discordant counts.

What iteration 2 tests (`docs/readiness/2026-10-09-slurp-nx-r1-i2-solver-fold-b-v1/`, the second and last evaluated
Solver round under the plateau rule): `r1-i2-c1` c5 plus an empty decision taken after extraction and gated on heard
values; `r1-i2-c2` c5 plus one soft empty sentence; `r1-i2-c3` c3 plus c5's filler conventions (declared carrier,
+1.54 pp class-split); `r1-i2-c4` c5 plus c2's heard-span anti-copy block; `r1-i2-c5` c5 with the contract
tightening removed (ablation). It decides on the official pooled column with the twin and intent guard above, and a
pick is confirmed once on TRAIN Fold A as a two-arm column before any lock.

## 7. Pending

The recipe's third family, the offline post-processing columns **v4** and **v4g** over every arm's delivered column
(`v4(X) - X`, `v4g(X) - X`, `v4g(X) - lock`), including the fresh-roster confirmation **`v4g(lock) - lock`** (lock rule:
CI95 lower bound > 0 on this Fold B column), is not on file: no `offline-v4/` folder exists under the analysis root at
the time of writing. These columns are appended to this note by a successor paragraph once the apply driver's
base-column fix lands. No number is stated here for them.

*Superseded for the post-processing family by "7 (successor)" at the end of this note, appended 2026-10-09 after the
registered `offline-v4/` reports landed. The paragraph above is kept as written.*

The review-off vs full-graph comparison (package README section 6, cross-flight against the P-SV-3 `a-agree` column) is
likewise not part of this note.

## 8. Reproduce

Run from the study root in WSL (`source ~/.venvs/speechrl/bin/activate`; `SPEECHRL_DATA_DIR` set). The read is
model-free and refuses unless the READ row is root countersigned.

```bash
# identities only; opens no gold, runs no scorer
bash scripts/analysis/nx_r1_read.sh --iteration 1 --dry-run
# the registered read: node-local (v1 at the time), seven official column scorings, aa-vs-lock and <candidate>-vs-lock
bash scripts/analysis/nx_r1_read.sh --iteration 1 --skip-offline
# the schema-v2 node-local re-read (normalised primary) into its own subfolder
bash scripts/analysis/nx_r1_read.sh --iteration 1 --node-local-out node-local-v2
# verify the on-file bytes quoted above
A=$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-COLUMN-READ-V1
sha256sum $A/node-local/report.json $A/node-local-v2/report.json $A/*-vs-lock/score-contrasts.json
```

The official column step is idempotent (skipped when `supply-variants/score-summary.json` carries the first-visit
schema; `--rescore` forces it) and a pass directory that already holds files is never overwritten.

## 7 (successor). Offline post-processing columns v4 and v4g (registered, appended 2026-10-09)

Appended by Claude Opus 5.5 (analysis agent, on the coordinator's brief, Fable 5.1) in the worktree
`fable/nx-v4g-lock`. This section only reads the fourteen write-once reports of the registered apply read
`SAEA-SLURP-NX-POSTPROC-V4-APPLY-V1` (driver `scripts/analysis/slurp_nx_postproc_v4_apply.py`, sha256
`4b979a8a4320b6c85497ab0f948670d13628d5e1601f030b5d01adfcb5d98717`; admitted on Fold B by this cell's recipe
`slurp-nx-r1-solver-fold-b-column-analysis-v1`, sha256 `7a4ac484...`); it opened no model, server, encoder, embedder,
tokenizer or GPU and ran no scorer. Every report is status DESCRIPTIVE and records contacts `model 0, gpu 0, network
0, paid_api 0` and two registered-scorer-on-copy runs (`slurp-slu-official-train`, CPU). **The verdict of section 5
is unchanged**: post-processing is a delivery-side component read beside the Solver arms, not a Solver arm.

**Construction.** For each arm X of the run, the base is X's NORMALISED column (X's first-visit Solver answer after
the cell's sealed `saea-deliver-normalise-v3`, via `stage3_rollout_score.normalise_arm_answer`); `v4(X)` / `v4g(X)`
apply the registered `saea-deliver-normalise-v4` / `saea-deliver-normalise-v4g` (version 1, the pinned TRAIN tables of
`docs/receipts/knowledge/slurp-v4-train-statistics-v1.json`) on top. Both the edited and the unmodified column are
written as derived copies and scored by the registered scorer; the scorer reproduces the in-process pooled SLU-F1 to
1e-6 on every copy, and every unmodified column reproduces the official column of section 2 (lock 62.13, aa 62.70,
c1 61.40, c2 62.35, c3 63.09, c4 61.93, c5 61.98; intent identical). Paired delta edited minus unmodified,
whole-utterance cluster bootstrap (1,080 clusters, 10,000 draws, seed 20260915), CI95. Rows applied 1,077 to 1,080
(the 0 to 3 unparsed rows per arm stay unmodified). Neither normaliser moves an intent label: the intent delta is
0.00 [0.00, 0.00] on all fourteen columns. Report path:
`$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-NX-POSTPROC-V4-APPLY-V1/offline-v4/<v4|v4g>-<arm>/report.json`.

| arm X | X official SLU-F1 | v4(X) - X pp [CI95] (rows edited) | v4(X) SLU-F1 | v4g(X) - X pp [CI95] (rows edited) | v4g(X) SLU-F1 | intent delta (both) | v4g(X) - lock, point only |
| --- | ---: | --- | ---: | --- | ---: | --- | ---: |
| `lock` | 62.13 | +1.44 [+0.62, +2.27] (118) | 63.57 | **+1.55 [+0.81, +2.33]** (104) | **63.69** | 0.00 | +1.55 |
| `aa` | 62.70 | +1.25 [+0.42, +2.09] (112) | 63.95 | +1.52 [+0.81, +2.29] (97) | 64.22 | 0.00 | +2.09 |
| `r1-c1` | 61.40 | +2.19 [+1.32, +3.07] (139) | 63.59 | +2.21 [+1.44, +3.03] (119) | 63.61 | 0.00 | +1.48 |
| `r1-c2` | 62.35 | +1.83 [+0.98, +2.69] (116) | 64.18 | +1.84 [+1.08, +2.64] (99) | 64.19 | 0.00 | +2.06 |
| `r1-c3` | 63.09 | +0.44 [-0.35, +1.23] (79) | 63.53 | +0.81 [+0.12, +1.53] (69) | 63.90 | 0.00 | +1.77 |
| `r1-c4` | 61.93 | +1.42 [+0.64, +2.22] (114) | 63.36 | +1.51 [+0.82, +2.24] (97) | 63.44 | 0.00 | +1.31 |
| `r1-c5` | 61.98 | +1.47 [+0.63, +2.33] (112) | 63.44 | +1.58 [+0.82, +2.37] (98) | 63.56 | 0.00 | +1.43 |

The SLU-F1 columns are the registered scorer's official pooled SLU-F1 on the derived copy. The last column is
arithmetic on two absolute levels of the same 1,080 rows (v4g(X) minus lock's 62.13); it was not bootstrapped and is
not a nomination input.

**The fresh-roster confirmation.** `v4g(lock) - lock` = **+1.55 pp [+0.81, +2.33]** (104 rows edited, intent 0
rows; official SLU-F1 62.13 -> 63.69; span-F1 +2.08 pp; equal-scenario +1.76). Its CI95 lower bound is **above 0**.
This is the registered confirmation of the guarded post-processing set on a roster that had not seen the rule
question: the v4 rules were selected on A2 (DEV-2000-ADDED), Fold A located the audio defect that the guards answer,
and TRAIN Fold B entered neither step. Report `offline-v4/v4g-lock/report.json` sha256
`7f2d22be05a4d36be484b13e0a34ed4066753d9c9bb337b4e042479faa6af6c4`; edited copy
`2f74c0727aae64f766305c4735937be5e627aa2ce8687cbe79d503c1e0434e87` (scorer result `a4c47abe...`), unmodified copy
`63d26c02da7ef946f5c37f5d75ccfe4e160f824b67821f737b2f65c6251378a4` (byte-identical to the v4-lock report's unmodified
copy). The lock itself is recorded in `docs/results/2026-10-09-slurp-postprocessing-v4g-lock-v1.md`.

**The audio stratum (60 rows; why the guards matter).** Unguarded v4 repeats on Fold B the loss Fold A found: audio
-10.13 (lock, 13 rows edited), -15.58 (aa), -16.35 (c1), -14.04 (c2), -26.62 (c3), -14.02 (c4), -13.41 (c5). Under
v4g the audio delta is +7.05 (lock, 6 rows), +6.55, +7.05, +4.92, 0.00 (c3, 0 rows edited), +4.69, +3.96. v4g(lock)
scenario losses are three small ones: datetime -0.84, lists -1.10, takeaway -1.15 (15 up, 3 down). Equal-scenario
deltas, v4 -> v4g: lock +1.11 -> +1.76, aa +0.69 -> +1.71, c1 +1.50 -> +2.22, c2 +1.27 -> +1.85, c3 -0.84 -> +0.52,
c4 +0.82 -> +1.49, c5 +0.92 -> +1.57.

**Why c3's v4g gain is smaller.** `r1-c3` already takes an explicit empty-entity decision in the Solver; that
decision overlaps what ee10 (and in part ti1) do downstream, so v4g has less left to remove on c3 (69 rows edited
against 97 to 119 on the other arms; +0.81 against +1.51 to +2.21; no audio row edited). In the composed point
column the advantage c3 showed over lock on the v3 column (+0.96) shrinks to +0.21 once both carry v4g (63.90 vs
63.69, arithmetic, not bootstrapped). This is consistent with section 5: c3's pooled gain is largely
false-positive removal that the guarded normaliser also delivers without the Solver's non-empty losses.

Report sha256 (all under `offline-v4/`): v4-lock `8e475293...`, v4g-lock `7f2d22be...`, v4-aa `47564117...`, v4g-aa
`4f175d3f...`, v4-r1-c1 `0da928c2...`, v4g-r1-c1 `afb7b964...`, v4-r1-c2 `5d99077a...`, v4g-r1-c2 `d61d947c...`,
v4-r1-c3 `173696a9...`, v4g-r1-c3 `8749741a...`, v4-r1-c4 `710d82c9...`, v4g-r1-c4 `29a54291...`, v4-r1-c5
`e82c8632...`, v4g-r1-c5 `c1e94910...`.
