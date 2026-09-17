# Cell B0 verdict: review loop off (module M0) on TRAIN A

Status: **HARMFUL** by the preregistered rule (intent clause), a width failure with a nil point
estimate; a same-roster own-null replicate and a re-decision rule are registered
(`docs/readiness/2026-09-17-slurp-b0-replicate-v1-preregistration.md`). Root: Fable 5.1,
2026-09-17. Program: `docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md`.
Preregistration: `docs/readiness/2026-09-17-slurp-b0-review-off-v1-preregistration.md`.

## What flew

Run SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-V1, attempt
attempt-slurp-native-review-off-train-fold-a-generation-v1, FINALIZED, manifest COMPLETED at
study commit 5d0d694d9f51002b026760122e43315f321acd1b (clean detached worktree), composed config
45fe779f75694774a5e8f313a6682da5f70531c6e810554b6cd1a06c734400d1, protocol
c445394b3c5560e07d4b1bf22b520297514456f88ca50d7293bb265f6090a7e6, attached to session
serving-slurp-native-candidate-five-train-a-np4-v1. The retained dual-store agent with the
Reviewer/Planner loop switched off: Perception -> Solver -> deliver, 2 contacts per row, prompts
byte-identical to the anchor's Perception and first Solver requests except the 8-byte program id
in the agent-control marker and the Solver epilogue's `max_revisions 0 / actions [ACCEPT]`.
Four-row smoke SAEA-SLURP-NATIVE-REVIEW-OFF-SMOKE-4-V1 sealed first (8 contacts, all fits).

| Artifact | SHA-256 |
| --- | --- |
| scores.json | 51f37e6c5a78751f2d000ac370cff6f0fff18745cd18d1fc81a2cd145ce960ae |
| run-manifest.json | 8b6f3f783f1933c4009c46cdc01472e240c547a496f7553c07e5efe301cdfe32 |
| outputs.jsonl | 108d6851c5cc5347e5b626354a99ea370f65d321c16396a914274e90c2678e65 |
| paired read `analysis/SAEA-SLURP-B0-REVIEW-OFF-PAIRED-ANALYSIS-V1/score-contrasts.json` | c26a76a3d7c24f41876a6a8fed6086d0620a6967ce09b7f687525996494c980e |

Rows: 1,080 scored, 1,071 parsed (9 malformed retained); every row's episode receipt carries
`review_loop_disposition = skipped_by_configuration`; zero tool calls. Comparators: the sealed
anchor SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1 (primary) and the released
direct anchor (secondary). Paired whole-speaker bootstrap, 10,000 draws, seed 20260915.

## B0 minus anchor (percentage points)

| Metric | Anchor | B0 | Delta | Speaker CI95 | Speaker CI90 | Equal-scenario |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| Official pooled SLU-F1 | 48.53 | 48.67 | +0.13 | [-1.15, +1.45] | [-0.94, +1.24] | +0.02 |
| Intent (scenario+action) | 77.96 | 77.59 | -0.37 | [-1.53, +0.82] | [-1.36, +0.61] | -0.37 |
| Scenario | 84.81 | 84.72 | -0.09 | [-1.29, +1.05] | [-1.11, +0.87] | -0.09 |
| Action | 79.26 | 78.70 | -0.56 | [-1.75, +0.69] | [-1.56, +0.49] | -0.56 |
| Pooled span F1 | 29.50 | 29.34 | -0.15 | [-1.74, +1.48] | [-1.47, +1.23] | -0.13 |
| Exact slot F1 (row mean) | 19.02 | 18.69 | -0.33 | [-1.34, +0.75] | [-1.19, +0.57] | -0.33 |
| SLU-F1 (row mean) | 30.29 | 29.83 | -0.46 | [-1.56, +0.71] | [-1.38, +0.48] | -0.46 |

Saves / harms / ties with the exact McNemar p: intent 22 / 26 / 1,032 (p = 0.67); scenario
21 / 22 / 1,037 (1.00); action 21 / 27 / 1,032 (0.47); exact slot F1 32 / 35 / 1,013 (0.81);
row SLU-F1 67 / 69 / 944 (0.93). The scenario-stratified sensitivity agrees everywhere.

## B0 minus the released direct anchor

Pooled SLU +14.78 [+11.90, +17.70]; intent +3.89 [+1.75, +6.11]; action +3.61 [+1.36, +6.09];
pooled span F1 +8.25 [+5.09, +11.39]; saves / harms intent 124 / 82 (p = 4e-3), row SLU-F1
296 / 79 (p = 1e-30). The two-contact agent keeps the whole dual-store gain over direct.

## Every scenario (natural mixture)

| Scenario | Anchor SLU | B0 SLU | Delta | Anchor intent | B0 intent | Delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 52.66 | 50.17 | -2.50 | 83.33 | 80.00 | -3.33 |
| audio | 47.75 | 42.02 | -5.74 | 76.67 | 76.67 | 0.00 |
| calendar | 48.38 | 48.61 | +0.23 | 75.00 | 70.00 | -5.00 |
| cooking | 62.47 | 62.18 | -0.29 | 85.00 | 86.67 | +1.67 |
| datetime | 59.52 | 58.10 | -1.42 | 83.33 | 86.67 | +3.33 |
| email | 36.64 | 35.32 | -1.32 | 85.00 | 85.00 | 0.00 |
| general | 15.45 | 15.69 | +0.23 | 36.67 | 31.67 | -5.00 |
| iot | 55.53 | 58.89 | +3.36 | 86.67 | 86.67 | 0.00 |
| lists | 43.55 | 45.62 | +2.07 | 83.33 | 81.67 | -1.67 |
| music | 34.53 | 33.83 | -0.70 | 76.67 | 80.00 | +3.33 |
| news | 44.24 | 45.14 | +0.90 | 80.00 | 80.00 | 0.00 |
| play | 46.82 | 49.83 | +3.01 | 58.33 | 53.33 | -5.00 |
| qa | 57.04 | 57.54 | +0.50 | 75.00 | 75.00 | 0.00 |
| recommendation | 49.75 | 51.98 | +2.23 | 90.00 | 88.33 | -1.67 |
| social | 34.74 | 40.73 | +6.00 | 66.67 | 70.00 | +3.33 |
| takeaway | 48.84 | 47.51 | -1.33 | 85.00 | 83.33 | -1.67 |
| transport | 51.34 | 48.16 | -3.18 | 86.67 | 88.33 | +1.67 |
| weather | 53.81 | 52.16 | -1.65 | 90.00 | 93.33 | +3.33 |

Ten scenarios up and eight down on pooled SLU; six up, seven down, five flat on intent; nothing
moves outside +-6 pp.

## Cost

| Figure | B0 | Anchor | Direct |
| --- | ---: | ---: | ---: |
| Generation contacts (per row) | 2,160 (2.00) | 5,417 (5.02) | 1,080 (1.00) |
| Repeated speech seconds | 6,169.06 | 15,459.76 | 3,084.53 |
| Prompt / completion tokens | 13,315,021 / 148,754 | 45,998,267 / 255,153 | 2,459,915 / 26,764 |
| GPU hours (monitor active seconds) | 1.054 | 3.388 | 0.087 |
| Generation wall seconds; slot occupancy; utilisation; parked | 3,945.1; 0.905; 86.4 %; 0.034 | -; -; 88.7 %; 0.022 | 450.6; 0.658; 55.7 %; 0.281 |
| FIT | 2,160 receipts, 8,640 endpoints, all fit, minimum margin 11,557 tokens | -- | -- |

Every registered ceiling held (contacts and FIT endpoints exactly at ceiling; speech 6,169.06 of
6,170; 1.054 of 2.0 GPU hours; one official scoring job). Against the anchor the module saves
60.1 % of contacts and speech seconds and 68.9 % of GPU hours.

## The rule, applied unchanged

- Clause 1 (SLU): CI95 lower bound -1.150 > -1.18: non-inferior TRUE; > 0 FALSE.
- Clause 2 (intent): CI95 lower bound -1.527 > -0.92: FALSE.

NEUTRAL needs both clauses; clause 2 fails, so the registered status is HARMFUL and, under the
runbook, later cells build on the sealed anchor until a re-decision.

## What the rule cannot see

This is a width failure, not a measured harm. The intent point estimate is -0.37 pp with 22
saves against 26 harms; the paired interval half-width on this roster is 1.175 pp at CI95 and
0.985 pp at CI90, both wider than the 0.92 pp margin imported from the DEV1000 own null (a CI90
half-width on a different roster with 124 speaker clusters of near-equal size; TRAIN A has 125
clusters of 1 to 56 rows). A null module therefore cannot pass clause 2 here at any interval
level, and the SLU clause passes by 0.03 pp. The imported margin does not transfer, the same
lesson the Earnings-21 own null taught on 2026-09-08.

The diagnostic isolates the ablated factor: the anchor's initial Solver intent equals its delivered
intent on 1,078 of 1,080 rows (five executed revisions, two intent changes), and B0's delivered
intent equals the anchor's initial Solver intent on 1,002 rows and its final intent on 1,001. Of
the roughly 78 rows where the arms disagree, at most one is attributable to the loop; the rest is
temperature-zero batch-composition nondeterminism, the known non-bitwise reproducibility of the
serving path.

## Decision

1. The registered status HARMFUL stands on record as the first-pass verdict; no default-plan entry
   for M0 is made from it. The harness-admission row for the loop is written at the re-decision,
   as the KC-E1f table entry was opened by its v2 decision with the v1 verdict beside it.
2. The family rule of 2026-09-08 requires margins from the carrier's own null on the same roster.
   A byte-identical same-roster replicate of B0 (run
   SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-REPLICATE-V1, 1.05 GPU hours) is registered with a
   re-decision rule fixed before it is read: own-null half-widths are the CI95 half-widths of
   (replicate minus B0) for pooled SLU and intent; NEUTRAL needs both passes non-inferior to the
   anchor at those margins; the first-pass status stays beside the re-decision as the KC-E1f v1/v2
   pair does. This is a measurement of the instrument, not a repeat to pass: the rule is fixed,
   the module's point estimate is already known to be nil, and the replicate is the same request
   bytes.
3. Until the re-decision, cells B1, B2 and B4 stay registered on the review-off base but do not
   fly; if the re-decision is HARMFUL they are re-based on the anchor before launch.
4. Independently of the guard, the efficiency finding is recorded: the review loop contributed
   at most two intent changes in 1,080 rows at 60 % of the contact budget.
