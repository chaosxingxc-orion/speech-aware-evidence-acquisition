# Cell REV-TFRL-1 (contrastive Reviewer form) read: intent -0.46 pp CI95 [-1.57, +0.65] and official SLU-F1 -0.55 pp [-1.79, +0.69] against the in-chain A/A on TRAIN Fold A (DESCRIPTIVE)

Read 2026-09-28 by Claude Opus 5.5 (worktree `/home/chao/saea-worktrees/fable-revtfrlread`, branch
`fable/revtfrlread`); the read drivers are model-free and do not invoke `core.flight.cli`. The registered read
(READ row `SAEA-SLURP-STAGE3-REVTFRL-FOLD-A-READ-V1`, ROOT COUNTERSIGNED 2026-09-28T15:17:46Z by the
coordinator, Fable 5.1, after the seal and before the read; owner decision 165; recipe
`slurp-stage3-revtfrl-fold-a-paired-analysis-v1`, `analysis-recipe-v1.json` sha256
`a2ee536b20a441ce60c65cdc458e2c9beb16ba3f07dace28e4a3aaa732d408bb`) ran once, between 15:18 and 15:23 UTC,
through `scripts/flights/read_paired_cell.sh docs/readiness/2026-09-27-slurp-stage3-reviewer-tfrl-v1 --passes vs-aa`
-> `scripts/analysis/stage3_paired_read.py` (sha256 `433bc936c0106f6377ed8ba693539f30dbe36014ec0622650ddafffb0656fad1`)
-> `scripts/analysis/slurp_paired_roster_read.py` (sha256
`2dca47e1c36be9f2174a58b48ee5db33b21a46273d9365e8d8e169f01566bd32`): seed 20260927, 10,000 paired draws, the row
as the resampling unit (cluster key `sample_id`), TRAIN gold through `slurp-slu-official-train`. The recipe
names no comparator, so only the gating pass `vs-aa` exists. Beside it: the per-role tokens by
`scripts/analysis/stage3_wave_beside_read.py` (sha256 `3075080ed77738ef8500ad208638bd21a2e14fa16a57c5f0be900526912ad2f7`)
and the node credit (recipe steps 2 and 4) by `scripts/analysis/slurp_revtfrl_node_credit_read.py` (sha256
`a40a3653e822445d6ccc3661a293edecc5131067fc69113a18436ad3610d65ea`), which applies
`scripts/analysis/slurp_reviewer_credit_table.py` (sha256
`184446b1b736334eb07750f04b31b28daca7a4c3f268a4240304068be90746e3`) unmodified. The three drivers ran from this
worktree (by the predecessor read agent) after the countersignature was written and before it and the
node-credit script were committed; the driver bytes are the committed bytes (the stored driver copies under
`vs-aa/` hash identically). A second invocation of the paired driver was refused because `vs-aa/` already
holds files; nothing was overwritten.

Analysis root `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-REVTFRL-FOLD-A-READ-V1/`:

| artefact | sha256 |
| --- | --- |
| `vs-aa/README.md` | `756506d528a7f446524070c57764f6bcfec7c8bba77413bbb563481dfc7d03be` |
| `vs-aa/verdict.json` | `c0dd4c392f572186ca93fb51279bad91528cb0e4ee2a10c8bf66838fb1b17db1` |
| `vs-aa/score-contrasts.json` | `480598ff3bf5b4917d74600fcd5304982d0abb36a20cc63c0a5e85aa4ddc2974` |
| `vs-aa/per-scenario-tables.json` | `e8b7220df7ff2e29ede17f7b70a82aefbc0b664b89d4bced4458a687ece2906d` |
| `vs-aa/structural.json` | `9810c3583e02ee3b9ee4f819a307cb2c09c79c2b2a9d65a3145f4fdea7579fe7` |
| `vs-aa/efficiency.json` | `7d697da0d21a7247de187aa7437c891d8030579b55bf0a05991c4dd3d2d1ec32` |
| `vs-aa/frontier.json` | `7d187d2a3a89c7edee11bb4200fdcde7b993b8a05cfc97ed6e296caf6b29ff1c` |
| `vs-aa/delivery-conversion.json` | `55f03158b18fc476cfa86b442d6f88de6f68df1b3842c5039859460205b88f84` |
| `vs-aa/stop.json` (PASSED) | `452418259cf4515644136efd3eef64c38aa2bdc0b69d3ad12fddee55919959d1` |
| `beside/beside-v1.json` | `d058a2f808fe76b1e269a20a55f834d3fe66fc17ca66e069d0f2bc7a31c1b3f1` |
| `node-credit/node-credit-v1.json` | `c9c346d45e54ce752cd877900826a08b0a419e5433bd4b0b80d1a1c90495d1fa` |

Model-free throughout: zero model, tokenizer, encoder, embedder, scorer-subprocess, server, network and GPU
contacts; the official scorer ran once per arm at finalize and its sealed per-sample output is read. Gold
enters only offline and is compared in memory. No utterance text, gold label string, intent name, slot
filler, Reviewer text or model output is printed or persisted here or in the receipts.

**DESCRIPTIVE.** The numbers and the side of the pre-declared rule they fall on; the verdict word is the
coordinator's (decision 139). A development read on a TRAIN construction fold (decisions 28, 86); never a
test claim.

## 1. Arms

| role | run id | manifest sha256 | scores sha256 |
| --- | --- | --- | --- |
| arm (contrastive Reviewer instruction `probes/slurp_native_role_reviewer_contrastive_v1.txt`) | `SAEA-SLURP-STAGE3-REVTFRL-FOLD-A-V1` | `4bbd179260ffdafb848faaebf78800c78c5310218c51f184c4068b0cab864066` | `2ea831497fc1d55e0b85d0db47db01ffe4cb5ff3761161ba9530a34174043114` |
| in-chain A/A (the G5 Reviewer file; gating) | `SAEA-SLURP-STAGE3-REVTFRL-AA-FOLD-A-V1` | `31555e739eeeeb3ddd4f73a3811692bb215db39e2390bb28e7066d16d041cdfe` | `f08b5d29302baa03bf5178957dc57f20fb9506d6a64b00f387067db4720f57ab` |

Both COMPLETED at 1,080 rows on the committed Fold A roster (split identity
`61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`), study commit 5f8b4c9d; 0 tool schemas and
0 tool calls on every contact of both arms; the recomputed official pooled SLU-F1 and span-F1 match the sealed
official values to 1e-15 on both arms (`stop.json` PASSED); the credit module's port agrees with the sealed
per-row intent and SLU counts on 1,080 / 1,080 rows of each arm.

## 2. The paired system read (arm minus in-chain A/A, n = 1,080)

| metric | A/A % | arm % | delta pp | CI95 pp | saves | harms | ties |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| intent (`scenario_action_exact`, primary) | 86.02 | 85.56 | -0.46 | [-1.57, +0.65] | 15 | 20 | 1045 |
| official pooled SLU-F1 micro (guard) | 64.76 | 64.22 | -0.55 | [-1.79, +0.69] | -- | -- | -- |
| per-row SLU-F1 | 43.66 | 43.09 | -0.58 | [-1.57, +0.44] | 44 | 62 | 974 |
| action exact | 86.67 | 86.48 | -0.19 | [-1.20, +0.83] | 15 | 17 | 1048 |
| scenario exact | 89.63 | 89.91 | +0.28 | [-0.56, +1.11] | 12 | 9 | 1059 |
| span-F1 micro | 54.55 | 53.97 | -0.58 | [-2.11, +0.94] | -- | -- | -- |

Intent McNemar p 0.4996; per-row SLU-F1 McNemar p 0.0982.

| weighting | intent delta pp | intent CI95 pp | SLU-F1 delta pp | SLU-F1 CI95 pp |
| --- | ---: | --- | ---: | --- |
| natural mixture | -0.46 | [-1.57, +0.65] | -0.55 | [-1.79, +0.69] |
| equal scenario (18 x 60) | -0.46 | [-1.48, +0.56] | +0.10 | [-1.23, +1.50] |

Per channel (intent): far-field (n 557) 86.00 -> 84.56, -1.44 pp, 5 saves / 13 harms; headset (n 523)
86.04 -> 86.62, +0.57 pp, 10 saves / 7 harms.

## 3. The pre-declared rule and the side the numbers fall on

The rule (recipe `decision_rule`, owner decision 127): NO-HARM ADMITTED when, against the in-chain A/A, the
intent CI95 lower bound is not below -0.9943 pp AND the official pooled SLU-F1 CI95 lower bound is not below
-1.2485 pp; HARMFUL on a measured loss on either metric (CI95 upper bound below zero, decision 25); never
reported as a gain.

| clause, against the in-chain A/A | measured | clause met |
| --- | --- | --- |
| intent CI95 lower bound >= -0.9943 (no-harm, primary) | -1.57 | no (short by 0.58 pp, about six rows) |
| official pooled SLU-F1 CI95 lower bound >= -1.2485 (no-harm, guard) | -1.79 | no (short by 0.54 pp) |
| intent CI95 upper bound < 0 (harm) | +0.65 | no |
| official pooled SLU-F1 CI95 upper bound < 0 (harm) | +0.69 | no |

Neither no-harm clause holds and neither harm clause is met: the numbers fall in the residual branch the rule
does not name (neither no-harm nor harm is shown). Under the equal-scenario weighting the SLU-F1 lower bound
(-1.23) sits inside its margin and the intent lower bound (-1.48) does not.

The declared expectation, +0.80 pp intent (interval +0.12 to +1.48; measured, decision 139), lies above the
system read's CI95 upper bound (+0.65) and above the loop-value difference's upper bound (+0.741, section 4).
The margins are the Fold A own-null half-widths h_intent 0.9943 and h_SLU 1.2485.

## 4. The Reviewer node credit (recipe steps 2 and 4)

| quantity | A/A | arm |
| --- | ---: | ---: |
| Reviewer visits (phases) | 1,113 | 1,544 |
| Reviewer visits per row, histogram | 0: 1, 1: 1,045, 2: 34 | 1: 616, 2: 464 |
| Reviewer visits per row | 1.031 | 1.430 |
| Planner routes ACCEPT / REVISE | 1,076 / 37 | 1,072 / 472 |
| REVISE rate per Reviewer visit | 3.32 % | 30.57 % |
| rows with any REVISE | 34 (3.15 %) | 464 (42.96 %) |
| revisions executed | 34 | 464 |
| Reviewer stance ENDORSE / ISSUE / NONE (gold-free flags) | 669 / 51 / 393 | 202 / 1,333 / 9 |
| Reviewer responses echoing the draft | 455 | 0 |
| Reviewer responses narrating a tool call | 0 | 0 |
| revisions changing intent / entities | 12 / 13 | 38 / 63 |
| intent repairs / breaks (revised visits) | 5 / 3 | 14 / 15 |
| entity repairs / breaks (revised visits) | 6 / 3 | 34 / 16 |
| entity error delta over revised visits | -11.91 | -49.32 |

Per pre-review error class (`credit_table`): visits, REVISE routes, intent repairs / breaks and entity
repairs / breaks on revised visits.

| pre-review class | A/A visits | A/A REVISE | A/A intent +/- | A/A entity +/- | arm visits | arm REVISE | arm intent +/- | arm entity +/- |
| --- | ---: | ---: | --- | --- | ---: | ---: | --- | --- |
| CORRECT | 519 | 5 | 0 / 2 | 0 / 1 | 662 | 164 | 0 / 8 | 0 / 7 |
| ENT-FP | 136 | 5 | 0 / 1 | 2 / 0 | 196 | 70 | 0 / 4 | 12 / 1 |
| ENT-FN | 87 | 0 | -- | -- | 123 | 23 | 0 / 0 | 1 / 0 |
| ENT-MIXED | 202 | 6 | 0 / 0 | 4 / 1 | 292 | 96 | 0 / 3 | 10 / 6 |
| INT-SHORTLIST | 78 | 11 | 5 / 0 | 0 / 1 | 130 | 54 | 10 / 0 | 8 / 2 |
| INT-OFFLIST | 89 | 10 | 0 / 0 | 0 / 0 | 139 | 64 | 4 / 0 | 3 / 0 |
| UNPARSED | 2 | 0 | -- | -- | 2 | 1 | 0 / 0 | 0 / 0 |

The loop value (delivered answer minus the same trajectory's first Solver draft, credit-module port,
whole-utterance cluster bootstrap, 2,000 draws, seed 20260927):

| quantity | A/A | arm | arm minus A/A (paired) |
| --- | ---: | ---: | ---: |
| first-draft intent % | 85.833 | 85.648 | -- |
| first-draft intent-wrong rows | 153 | 155 | -- |
| delivered intent % | 86.019 | 85.556 | -- |
| loop value, intent pp | +0.185 [-0.278, +0.741] | -0.093 [-1.019, +0.833] | -0.278 [-1.296, +0.741] |
| first-draft SLU-F1 % | 64.621 | 63.758 | -- |
| delivered SLU-F1 % | 64.763 | 64.217 | -- |
| loop value, SLU-F1 pp | +0.142 [-0.251, +0.547] | +0.459 [-0.296, +1.245] | +0.317 [-0.403, +1.079] |

The arm's first drafts already differ from the A/A's (SLU-F1 63.76 vs 64.62, intent-wrong rows 155 vs 153)
before any review; the Perception and Solver prompts are byte-identical between the arms, so the first-draft
gap is between-flight nondeterminism (greedy decoding is not bitwise reproducible across flights). Delivery is
identical: the gold intent boundary is delivered on 1,040 / 1,040 rows on both arms; among the
delivered-in-both rows 15 go wrong -> right and 20 right -> wrong.

## 5. Per scenario (intent and official SLU-F1, n = 60 each; CI95 paired cluster bootstrap, 10,000 draws)

| scenario | intent A/A | intent arm | delta pp | CI95 pp | saves | harms | SLU A/A | SLU arm | delta pp | CI95 pp |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| alarm | 93.33 | 91.67 | -1.67 | [-8.33, +5.00] | 2 | 3 | 68.98 | 74.45 | +5.47 | [+1.04, +11.20] |
| audio | 78.33 | 78.33 | 0.00 | [-6.67, +6.67] | 2 | 2 | 60.99 | 68.82 | +7.83 | [-1.37, +21.89] |
| calendar | 93.33 | 91.67 | -1.67 | [-5.00, 0.00] | 0 | 1 | 65.55 | 65.34 | -0.21 | [-2.78, +1.93] |
| cooking | 85.00 | 81.67 | -3.33 | [-8.33, 0.00] | 0 | 2 | 63.34 | 64.55 | +1.22 | [-0.76, +3.58] |
| datetime | 91.67 | 91.67 | 0.00 | [0.00, 0.00] | 0 | 0 | 75.79 | 78.00 | +2.21 | [-2.71, +7.91] |
| email | 90.00 | 86.67 | -3.33 | [-8.33, 0.00] | 0 | 2 | 64.35 | 63.48 | -0.88 | [-4.00, +1.76] |
| general | 50.00 | 48.33 | -1.67 | [-8.33, +5.00] | 2 | 3 | 19.05 | 22.73 | +3.68 | [-2.48, +13.51] |
| iot | 83.33 | 86.67 | +3.33 | [0.00, +8.33] | 2 | 0 | 68.44 | 63.53 | -4.91 | [-12.94, +1.82] |
| lists | 90.00 | 90.00 | 0.00 | [0.00, 0.00] | 0 | 0 | 58.21 | 58.21 | -0.00 | [-8.14, +8.19] |
| music | 81.67 | 83.33 | +1.67 | [-5.00, +8.33] | 3 | 2 | 49.74 | 49.62 | -0.13 | [-4.77, +3.83] |
| news | 86.67 | 90.00 | +3.33 | [0.00, +8.33] | 2 | 0 | 70.01 | 71.27 | +1.27 | [-4.26, +7.13] |
| play | 88.33 | 88.33 | 0.00 | [0.00, 0.00] | 0 | 0 | 54.95 | 54.47 | -0.47 | [-6.14, +5.11] |
| qa | 91.67 | 88.33 | -3.33 | [-8.33, 0.00] | 0 | 2 | 64.95 | 64.12 | -0.83 | [-3.53, +1.67] |
| recommendation | 98.33 | 96.67 | -1.67 | [-5.00, 0.00] | 0 | 1 | 72.37 | 67.72 | -4.65 | [-10.88, +1.54] |
| social | 81.67 | 81.67 | 0.00 | [0.00, 0.00] | 0 | 0 | 60.37 | 58.23 | -2.14 | [-7.01, +2.69] |
| takeaway | 83.33 | 80.00 | -3.33 | [-8.33, 0.00] | 0 | 2 | 59.59 | 56.68 | -2.91 | [-7.50, +1.76] |
| transport | 85.00 | 88.33 | +3.33 | [0.00, +8.33] | 2 | 0 | 67.23 | 64.12 | -3.11 | [-7.97, +1.36] |
| weather | 96.67 | 96.67 | 0.00 | [0.00, 0.00] | 0 | 0 | 78.23 | 78.54 | +0.30 | [-4.02, +4.83] |

Both weightings of the pooled deltas are the section 2 rows (the roster holds 60 rows per scenario; within a
scenario cell the two weightings coincide).

## 6. Tokens, GPU-hours and the frontier row (decision 75)

| field | A/A | arm | arm minus A/A |
| --- | ---: | ---: | ---: |
| contacts | 4,421 | 5,712 | +1,291 |
| contacts per row | 4.0935 | 5.2889 | +1.1954 |
| prompt tokens per row | 35,157.7 | 48,557.5 | +13,399.9 |
| prefilled tokens per row | 8,661.7 | 9,314.7 | +653.1 |
| completion tokens per row | 214.4 | 310.7 | +96.3 |
| GPU-hours (1,080 rows) | 1.6467 | 2.0692 | +0.4225 |
| GPU-hours per 1,000 rows | 1.5247 | 1.9159 | +0.3912 |
| official intent % | 86.02 | 85.56 | -0.46 |
| official SLU-F1 % | 64.76 | 64.22 | -0.55 |

Per role, A/A / arm (contacts; completion tokens per contact; prefilled tokens per contact): Perception
1,080 / 1,080, 118.2 / 117.4, 1,369.2 / 1,373.4; Planner 1,113 / 1,544, 2.0 / 2.3, 237.1 / 277.7; Reviewer
1,114 / 1,544, 67.3 / 109.0, 186.1 / 385.9; Solver 1,114 / 1,544, 24.0 / 23.9, 6,646.9 / 4,891.1. Frontier
ratios: intent -0.2237 pp per GPU-hour per 1,080 rows; -0.0497 pp per 1,000 prefilled tokens per row.

## 7. Notes on the read

- Recipe step 5 asks for the arm's credit table next to the sealed source arm's (the confound check). The
  source figures are the recipe's own R01C statistic (contrastive loop +2.56 pp, locked +0.738 pp, paired
  +1.697 [+0.263, +3.143] on 625 rows outside Fold A, first-draft intent-wrong rate 30.00 %); this read
  computes no new R01C number. The Fold A first-draft intent-wrong rate is 153 / 1,080 = 14.17 % on the A/A,
  the base rate the expectation assumed.
- The Reviewer contact count differs by one between the trace token accounting (A/A 1,114) and the phase
  summaries (A/A 1,113 visits, one row with no Reviewer visit); the credit table uses the phase count.
- Step 6 (hand the arm's per-visit credit table to the next proposer round) is the coordinator's; the table is
  `node-credit/node-credit-v1.json`, key `credit.arm`.

## Coordinator verdict (Fable 5.1, 2026-09-29)

**NOT ADMITTED (neutral by width with a measured cost).** Against the in-chain A/A (n = 1,080), intent
-0.46 [-1.57, +0.65] and official SLU-F1 -0.55 [-1.79, +0.69]: both no-harm clauses fail (each lower end
sits below its margin) and no harm clause is met (each interval contains zero), so by the registered rule
the cell is neutral by width; the declared +0.80 pp intent expectation lies above the whole CI. The
contrastive form achieved reach -- REVISE rose from 3.32 % to 30.57 % of Reviewer visits -- but not
judgment: on revised visits intent repairs / breaks are 14 / 15 and entity repairs / breaks 34 / 16, so
more revisions did not make the Reviewer's calls better. The cost is measured: +0.42 GPU-h per 1,080 rows
(1.6467 -> 2.0692). Owner decision 188: the Reviewer's second TF-RL round (B5, the Reviewer top-2
contrast) is deferred behind the Perception-phase cells P-SV-1 / P-SV-2 (row 184); row 165's route stays
open, and B5 is offered afterwards only if P-SV shows that contrastive evidence moves the deciding node.
The agent's numbers above are unchanged.
