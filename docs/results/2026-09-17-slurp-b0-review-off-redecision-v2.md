# Cell B0 re-decision v2: review loop off (module M0) under the TRAIN A own null

Status: **HARMFUL** under the preregistered re-decision rule (both clauses fail on intent; the
SLU clause fails on the first pass by 0.028 pp). The Reviewer/Planner loop stays in the default
plan; every later cell builds on the sealed dual-store anchor. Root: Fable 5.1, 2026-09-17.
Preregistration: `docs/readiness/2026-09-17-slurp-b0-replicate-v1-preregistration.md` (section 6,
rule fixed before contact). First-pass verdict on record beside this one:
`docs/results/2026-09-17-slurp-b0-review-off-verdict.md`. Owner decision 6 of 2026-09-17.

## What flew

Run SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-REPLICATE-V1 (B0r), attempt
attempt-slurp-native-review-off-train-fold-a-replicate-generation-v1, FINALIZED, manifest
COMPLETED at study commit f38d3c33c26b51c3936d8f7f996772989978587c (clean detached worktree), a
byte-identical re-flight of cell B0's configuration: composed config
086b6387de1f5ef9afb4d86f7f90058c753f3fea78d9ed1ee3ea9ea960f3018a, protocol
6f1d8dc0120b5f87442ac0d48eb0ca63656603222326df13b159673fe05e7d48, attached to session
serving-slurp-native-candidate-five-train-a-np4-v1; rendered requests byte-identical to B0's on
1,080 rows and all four phases, proved before contact; no smoke (B0's covers the form).

| Artifact | SHA-256 |
| --- | --- |
| scores.json | 2974b45b5fa9087fa7b6d01029f62d75cec078abec36418d2deafa526cb48820 |
| run-manifest.json | 63a9be98e67a0e6e4625c9529e264024681a27adec72b790067e7e020f9fe183 |
| outputs.jsonl | 3212bcbc1913d8357ee101c2926e0df2292c39e33da874e4f5983440a09fe29f |
| paired read `analysis/SAEA-SLURP-B0-REPLICATE-PAIRED-ANALYSIS-V1/score-contrasts.json` | 69abec23e2c6aecca0d55474268ae2c9966631f243497f354a95b332c7ceb849 |

1,080 rows (1,073 parsed, 7 malformed retained), every row `skipped_by_configuration`, zero tool
calls, one official score. Costs: 2,160 contacts, 6,169.06 repeated speech seconds, prompt tokens
13,346,225, completion 149,087, 1.059 GPU hours, wall 3,941 s, occupancy 0.907, utilisation
87.7 %, parked 0.030; FIT 2,160 receipts / 8,640 endpoints, all fit, minimum margin 11,561.

## The own null: B0r minus B0 (same request bytes)

| Metric | B0 | B0r | Delta | CI95 | Half-width |
| --- | ---: | ---: | ---: | --- | ---: |
| Official pooled SLU-F1 | 48.665 | 48.629 | -0.037 | [-1.219, +1.024] | 1.122 = h_SLU |
| Intent (scenario+action) | 77.593 | 77.685 | +0.093 | [-0.911, +1.099] | 1.005 = h_intent |
| Scenario | 84.722 | 85.093 | +0.370 | [-0.673, +1.458] | 1.066 |
| Action | 78.704 | 78.981 | +0.278 | [-0.769, +1.296] | 1.033 |
| Pooled span F1 | 29.344 | 29.658 | +0.315 | [-1.309, +1.809] | 1.559 |

Saves / harms / ties: intent 22 / 21 / 1,037 (p = 1.00), row SLU-F1 64 / 60 / 956 (p = 0.79).
Seventy-seven rows (7.13 %) deliver a different intent between two byte-identical runs: the
temperature-zero batch-composition nondeterminism of the serving path, now measured on this
roster and geometry.

## The rule, clause by clause

| Clause | Margin | (B0 - anchor) CI95 lower | Passes | (B0r - anchor) CI95 lower | Passes | Holds |
| --- | ---: | ---: | --- | ---: | --- | --- |
| 1, pooled SLU | -1.122 | -1.150 | no | -1.043 | yes | NO |
| 2, intent | -1.005 | -1.527 | no | -1.313 | no | NO |

NEUTRAL needs both clauses on both passes; the intent clause fails on both. Status HARMFUL. The
gain test is not reached. Both anchor legs share the anchor's single realisation, so the
consistent negative sign of the intent deltas (-0.37 and -0.28 pp) is one reading of the
anchor's own draw, not two independent readings; the rule does not adjust for that and none is
applied here.

## B0r minus anchor and minus direct

Against the anchor: pooled SLU +0.10 [-1.04, +1.19]; intent -0.28 [-1.31, +0.73]; scenario +0.28;
action -0.28; pooled span F1 +0.16; saves / harms intent 22 / 25 (p = 0.77), row SLU-F1 66 / 67.
Per scenario the worst pooled-SLU losses are lists -6.95, datetime -3.09, general -2.41 and the
best gains qa +2.94, recommendation +2.86, news +1.68; on intent calendar and play lose 5.00 and
datetime gains 6.67 (full tables in the machine result). Against the released direct anchor:
pooled SLU +14.74 [+11.78, +17.68], intent +3.98 [+1.95, +6.11], span F1 +8.56.

## Projection v3 beside the rule (owner decision 7)

| Arm | v3 SLU | v3 intent | v3 span F1 | Labels / fillers changed |
| --- | ---: | ---: | ---: | --- |
| anchor | 51.99 | 79.35 | 40.30 | 20 / 195 |
| B0 | 52.16 | 79.07 | 40.60 | 27 / 179 |
| B0r | 51.91 | 79.44 | 39.91 | 31 / 180 |
| direct | 34.31 | 75.37 | 23.24 | 47 / 36 |

v3 contrasts: B0 - anchor SLU +0.16 [-1.34, +1.72], intent -0.28 [-1.26, +0.75]; B0r - anchor SLU
-0.08 [-1.37, +1.15], intent +0.09 [-0.85, +1.06]. The symmetric-normalised scorer
`slurp-slu-f1-normalized-v1` has no TRAIN sibling (it resolves gold from `devel` and refuses the
TRAIN roster), so the symmetric number is not available on this roster until one is registered.

## Consequences

1. Module M0 stays out of the default plan; the Reviewer/Planner loop is retained. The
   harness-admission table records the loop (`native_episode.review_loop`, class `episode`) as
   NEUTRAL: its own ON-minus-OFF deltas (+0.37 / +0.28 pp intent, -0.13 / -0.10 pp SLU) sit inside
   the own null, so it may stay in the default plan, and removing it failed non-inferiority on
   both passes, so it may not leave.
2. Cells B1, B2 and B4 re-register on the anchor base (v2 packages); the review-off packages are
   superseded before contact and their rows stay `consumed = no`.
3. The TRAIN A own null of this geometry is now measured: h_SLU 1.122 pp, h_intent 1.005 pp at
   CI95 (0.942 / 0.851 at CI90). Every later TRAIN A verdict uses these instead of the imported
   DEV1000 margins.
4. The cost fact stands: the loop is 3.26 contacts per row and 2.33 GPU hours per 1,080 rows for
   at most two changed delivered intents.

Addendum (2026-09-17, owner decision 14): the TRAIN symmetric re-read `docs/results/2026-09-17-slurp-train-symmetric-reread-v1.md` gives B0 minus anchor +0.08 [-1.40, +1.62] and B0r minus anchor -0.20 [-1.48, +1.04] symmetric SLU; the symmetric own null (B0r minus B0) has half-width 1.310 pp, wider than the official 1.122, so the program keeps the official margins; the normaliser touches no intent label, so this re-decision (which turned on intent) is structurally unaffected.
