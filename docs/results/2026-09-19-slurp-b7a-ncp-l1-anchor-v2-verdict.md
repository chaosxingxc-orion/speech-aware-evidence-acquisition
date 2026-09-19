# HARMFUL -- cell B7a v2 (Node Context Policy L1) on the sealed dual-store anchor, SLURP TRAIN A

Status: **HARMFUL**, the word the registered decision rule names. Against the sealed dual-store
anchor on the same 1,080 TRAIN Fold A rows the official pooled SLU micro F1 delta is **-0.3100 pp,
CI95 [-1.8072, +1.1211]** and intent (joint scenario+action) is **-0.6481 pp, CI95 [-2.1849,
+0.8688]**. Conjunct (a) fails -- the CI95 lower bound is not above zero -- and the NEUTRAL test
fails too, because **both** CI95 lower bounds fall below the imported own-null margins (SLU -1.8072
< -1.1218; intent -2.1849 < -1.0051). The rule's third branch is HARMFUL, and its stated
consequence is that **level L1 does not enter the SLURP default plan and cell B7b (level L2) is not
flown**.

**The verdict is driven by interval width, not by a measured loss.** Both point estimates sit well
inside the margins they must clear (-0.31 against 1.1218; -0.65 against 1.0051), and the two
conjuncts that do not depend on interval width both pass: every scoring agrees in sign (official
-0.3100, projection v3 -0.5029, TRAIN symmetric -0.6752) and **no scenario of the eighteen loses
intent beyond the null band**. What fails is that this cell's own CI95 half-widths -- **1.4641 pp
for SLU and 1.5269 pp for intent** -- are 30.5 % and 51.9 % wider than the B0r review-off values the
rule borrows. This verdict does not change the rule or the status; it records the fact, because the
same pattern closed cell B5e on 2026-09-18 and owner decision 25 (a combination cell called HARMFUL
needs a measured loss) scopes to combination cells only, so this single-factor cell's registered
rule reads exactly as written.

Root: the B7a v2 paired-read agent, 2026-09-19. Read **once**, from the single official score of the
complete manifest; no row was filtered and no repeat-to-pass was taken. Recipe:
`docs/readiness/2026-09-19-slurp-b7a-ncp-l1-anchor-v2/b7a-analysis-recipe-v2.json`.
Preregistration: `docs/readiness/2026-09-19-slurp-b7a-ncp-l1-anchor-v2-preregistration.md`, which
inherits the question, arms, metrics, resampling and decision rule of
`docs/readiness/2026-09-17-slurp-b7a-ncp-l1-anchor-v1-preregistration.md` unchanged, plus the
`planner_action_illegal` obligation of
`docs/readiness/2026-09-17-slurp-b7a-ncp-l1-anchor-v1-recovery-v1.md` section 8. The closed v1
flight: `docs/results/2026-09-19-slurp-b7a-v1-closure.md`.

## What flew

Run `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-V2`, attempt
`attempt-slurp-native-ncp-l1-anchor-train-fold-a-generation-v2`, **FINALIZED**, manifest
**COMPLETED** at study commit `83d6b1b2b93ceaec222338e1663afee786c018a9` with `study_repo_dirt`
**empty**, composed config `73a817ffda56b02501002685db0cd695516425644544fa040464efb17849d494` and
protocol `f5a6733f39952cfba2fc418d233c8acf1ff3a3758f16765737de47cc2fbceb31` -- the two values the v2
package registered pre-flip -- arm `speech-feature-query-native-tools`, profile
`bounded-discovery-probe`, split identity
`61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, role `discovery`, 1,080 ordered
ids. Sealed bytes, each re-hashed by this read before it was opened:

| artefact | SHA-256 |
| --- | --- |
| run manifest | `eb4714371aa95dedf13dfbaabb943e0b68d13b1a8e05ecd944a5c6b23db0a343` |
| official score | `e824f964b437875ccf2577be74ef57cc334a9ffbb79558a84cc827996c6de9dc` |
| outputs | `4aa2aee5d66d08d524cf224e6a85160e3bd6f1224afadacf23840cadd1ca75a0` |

One official complete scoring job through `core.scoring_batch`, never sharded, the number this
verdict reads.

**Both arms are NODE-FREE.** Cell B7a and the sealed dual-store anchor were both registered before
module M3, the delivery normaliser, entered the default plan, so neither arm carries it. The
projection-v3 reading is reported beside every official number as a **diagnostic only** (owner
decision 23 of 2026-09-18 keeps the decision number official and unprojected).

**The finite-completion policy is the one key that differs from the closed v1 recovery.** It was
**absent** on the anchor -- the parser's `"raise"` default -- and **armed**
(`deliver-latest-or-abstain`) on this arm. The exposure receipt
`docs/receipts/slurp-finite-completion-exposure-v1.json` records the anchor attempt at 5,417
contacts with `finite_contacts: []`, so the anchor met **zero** finite completions; this arm met
three, counted below.

## The STOP condition, closed before any B7a table was read

Both registered comparator aggregates reproduce from the sealed bytes, to the hundredth of a point,
and `analysis.null_calibration.pooled_f1` reproduces each of the three arms' own official pooled
aggregates to 1e-6:

| check | registered | recomputed |
| --- | ---: | ---: |
| anchor official SLU F1 | 48.53 | 48.5336 |
| anchor official intent | 77.96 | 77.9630 |
| anchor official scenario | 84.81 | 84.8148 |
| anchor official action | 79.26 | 79.2593 |
| anchor official span F1 | 29.50 | 29.4985 |
| direct official SLU F1 | 33.89 | 33.8926 |
| direct official intent | 73.70 | 73.7037 |
| direct official scenario | 82.69 | 82.6852 |
| direct official action | 75.09 | 75.0926 |
| direct official span F1 | 21.10 | 21.0967 |

The projection-v3 rescoring of both comparators reproduces their registered v3 readings as well
(anchor 51.9946 / 79.3519 / 85.4630 / 80.6481 / 40.3025 against the registered 51.99 / 79.35 /
85.46 / 80.65 / 40.30; direct 34.3137 / 75.3704 / 84.1667 / 75.9259 / 23.2359 against 34.31 / 75.37
/ 84.17 / 75.93 / 23.24).

## (a) B7a v2 minus the sealed dual-store anchor -- the PRIMARY contrast (percentage points)

delta = cell B7a v2 minus the anchor; negative is worse. Paired whole-speaker cluster bootstrap,
10,000 draws, seed 20260915, over the roster's 125 speaker clusters.

| metric | estimand | anchor | B7a v2 | delta | speaker CI95 | speaker CI90 | CI95 half-width | scenario-stratified CI90 | equal-scenario delta |
| --- | --- | ---: | ---: | ---: | --- | --- | ---: | --- | ---: |
| Official pooled SLU micro F1 | pooled count F1 | 48.53 | 48.22 | **-0.31** | [-1.81, +1.12] | [-1.54, +0.89] | 1.4641 | [-1.68, +1.09] | -0.95 |
| Intent (joint scenario+action) | mean per row | 77.96 | 77.31 | **-0.65** | [-2.19, +0.87] | [-1.93, +0.64] | 1.5269 | [-1.67, +0.46] | -0.65 |
| Scenario accuracy | mean per row | 84.81 | 84.54 | -0.28 | [-1.83, +1.20] | [-1.59, +0.96] | 1.5118 | [-1.30, +0.74] | -0.28 |
| Action accuracy | mean per row | 79.26 | 78.61 | -0.65 | [-2.22, +0.86] | [-1.97, +0.63] | 1.5384 | [-1.76, +0.46] | -0.65 |
| Official span F1 (pooled) | pooled count F1 | 29.50 | 29.38 | -0.12 | [-1.87, +1.65] | [-1.57, +1.37] | 1.7631 | [-1.94, +1.72] | -0.48 |
| Exact slot F1 (per-row mean) | mean per row | 19.02 | 20.35 | **+1.33** | [+0.15, +2.58] | [+0.35, +2.35] | 1.2137 | [+0.12, +2.54] | +1.33 |
| Official SLU F1 (per-row mean) | mean per row | 30.29 | 32.27 | **+1.98** | [+0.88, +3.15] | [+1.04, +2.94] | 1.1333 | [+0.90, +3.06] | +1.98 |

Saves, harms and ties, with the exact two-sided McNemar p:

| per-row metric | saves | harms | ties | exact two-sided McNemar p |
| --- | ---: | ---: | ---: | --- |
| scenario_action_exact (intent) | 23 | 30 | 1027 | 4.101e-01 |
| scenario_exact | 22 | 25 | 1033 | 7.709e-01 |
| action_exact | 24 | 31 | 1025 | 4.188e-01 |
| slot_f1_exact_f1 | 62 | 41 | 977 | 4.823e-02 |
| slu_f1_f1 | 108 | 82 | 890 | 6.944e-02 |

**The two per-row means move the other way.** Per-row exact slot F1 gains +1.33 pp with a CI95
lower bound above zero, and the per-row mean of official SLU-F1 gains +1.98 pp, likewise above
zero -- while the *pooled* count F1, which is the registered primary, loses 0.31 pp. The pooled
metric weights a row by its gold mention count and the per-row mean does not, so the two disagree
whenever a change helps sparse rows and costs dense ones. **This is reported, not interpreted: the
registered primary is the pooled number, and eight boundaries move together in this cell, so no
per-boundary attribution is available from it.**

## (b) B7a v2 minus the released direct anchor (secondary, never a gate)

| metric | direct | B7a v2 | delta | speaker CI95 |
| --- | ---: | ---: | ---: | --- |
| Official pooled SLU micro F1 | 33.89 | 48.22 | +14.34 | [+11.31, +17.33] |
| Intent (joint scenario+action) | 73.70 | 77.31 | +3.61 | [+1.47, +5.75] |
| Scenario accuracy | 82.69 | 84.54 | +1.85 | [-0.18, +3.99] |
| Action accuracy | 75.09 | 78.61 | +3.52 | [+1.42, +5.73] |
| Official span F1 (pooled) | 21.10 | 29.38 | +8.28 | [+5.19, +11.42] |
| Exact slot F1 (per-row mean) | 10.72 | 20.35 | +9.63 | [+7.64, +11.75] |
| Official SLU F1 (per-row mean) | 16.06 | 32.27 | +16.21 | [+14.11, +18.48] |

The system-over-direct margin is intact; the cell's own question is whether L1 moves the system
above the system anchor, and it does not.

## The rule, applied unchanged

Quoted verbatim from `docs/superpowers/specs/2026-09-17-node-context-policy-design.md` section 11,
carried unchanged into the recipe's `decision_rule`:

> ADMITTED iff the primary official SLU CI95 lower bound is > 0 against the anchor, intent is
> non-inferior at the own null margin 1.0051 pp, the symmetric-normalised scorer agrees in sign, and
> no scenario loses intent beyond the null band. NEUTRAL iff both primary metrics are non-inferior
> within the own null margins (SLU 1.1218, intent 1.0051); a NEUTRAL L1 still enters the SLURP
> default plan, because it removes a named defect class at no measured cost -- the seven malformed
> drafts that reached the Planner unflagged and the 2,167 unstructured reviews now carry a declared,
> receipted disposition. HARMFUL otherwise, and then L2 is not flown.

| conjunct | quantity | value | threshold | passes |
| --- | --- | ---: | ---: | --- |
| (a) primary | official pooled SLU delta, CI95 lower bound | **-1.8072** | > 0 | **no** |
| (b) intent guard | intent delta, CI95 lower bound | **-2.1849** | > -1.0051 | **no** |
| (c) sign agreement | unprojected -0.3100 vs projection v3 -0.5029 (and TRAIN symmetric -0.6752) | | same sign | yes |
| (d) scenario band | scenarios whose own intent CI95 upper bound is below zero | **0 of 18** | 0 | yes |
| NEUTRAL test | SLU CI95 lower -1.8072 > -1.1218 **and** intent CI95 lower -2.1849 > -1.0051 | | both | **no** |

**ADMITTED fails at (a). NEUTRAL fails because neither primary metric is non-inferior at its
imported margin. The rule's remaining branch is HARMFUL, and L2 is not flown.**

**The symmetric-normalised clause.** The recipe records the symmetric clause as NOT EVALUABLE on
this roster and substitutes the projection-v3 agreement clause (deviation 1 of the v1
preregistration, section 12). That recipe statement is **stale**: the TRAIN sibling
`slurp-slu-f1-normalized-v1-train` does resolve in `core.base.SCORERS` and the sealed B4b-rep read
of 2026-09-18 used it. This read therefore computed **both**, and they agree: symmetric -0.6752 pp
CI95 [-2.4201, +0.9610], same sign as the unprojected number, so conjunct (c) passes on either
reading and the substitution changes nothing here. **Where this read and the recipe disagree, the
recipe wins and the disagreement is stated -- this is the one place it arose.**

## Projection v3 and the TRAIN symmetric view, beside the rule

| arm | official pooled SLU F1 | v3 pooled SLU F1 | v3 intent | v3 scenario | v3 action | v3 span F1 | labels changed | fillers changed | symmetric pooled SLU F1 | symmetric span F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| anchor | 48.53 | 51.99 | 79.35 | 85.46 | 80.65 | 40.30 | 20 | 195 | 52.09 | 41.38 |
| **B7a v2** | **48.22** | **51.49** | **79.35** | **85.83** | **80.65** | **39.61** | 33 | 202 | **51.41** | **40.32** |
| direct | 33.89 | 34.31 | 75.37 | 84.17 | 75.93 | 23.24 | 47 | 36 | 34.46 | 24.38 |

| contrast | v3 pooled SLU delta | speaker CI95 | symmetric pooled SLU delta | speaker CI95 |
| --- | ---: | --- | ---: | --- |
| B7a v2 minus anchor | **-0.50** | [-2.26, +1.14] | **-0.68** | [-2.42, +0.96] |
| B7a v2 minus direct | +17.18 | [+14.02, +20.32] | +16.96 | [+13.86, +20.06] |

The same headline table under **projection v3**, beside the unprojected one above (B7a v2 minus the
sealed anchor):

| metric | anchor | B7a v2 | delta | speaker CI95 | speaker CI90 | equal-scenario delta |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| Official pooled SLU micro F1 | 51.99 | 51.49 | -0.50 | [-2.26, +1.14] | [-1.94, +0.88] | -1.18 |
| Intent (joint scenario+action) | 79.35 | 79.35 | +0.00 | [-1.19, +1.23] | [-1.01, +1.02] | +0.00 |
| Scenario accuracy | 85.46 | 85.83 | +0.37 | [-0.72, +1.46] | [-0.54, +1.28] | +0.37 |
| Action accuracy | 80.65 | 80.65 | +0.00 | [-1.23, +1.24] | [-1.03, +1.03] | +0.00 |
| Official span F1 (pooled) | 40.30 | 39.61 | -0.69 | [-2.54, +1.18] | [-2.25, +0.88] | -0.85 |
| Exact slot F1 (per-row mean) | 25.53 | 26.78 | +1.26 | [+0.01, +2.57] | [+0.21, +2.35] | +1.26 |
| Official SLU F1 (per-row mean) | 32.97 | 34.93 | +1.96 | [+0.74, +3.23] | [+0.93, +2.99] | +1.96 |

And under the **TRAIN symmetric** normaliser:

| metric | anchor | B7a v2 | delta | speaker CI95 | speaker CI90 | equal-scenario delta |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| Official pooled SLU micro F1 | 52.09 | 51.41 | -0.68 | [-2.42, +0.96] | [-2.10, +0.71] | -1.35 |
| Intent (joint scenario+action) | 77.96 | 77.31 | -0.65 | [-2.18, +0.87] | [-1.93, +0.64] | -0.65 |
| Scenario accuracy | 84.81 | 84.54 | -0.28 | [-1.83, +1.19] | [-1.59, +0.96] | -0.28 |
| Action accuracy | 79.26 | 78.61 | -0.65 | [-2.22, +0.86] | [-1.97, +0.63] | -0.65 |
| Official span F1 (pooled) | 41.38 | 40.32 | -1.06 | [-3.01, +0.95] | [-2.71, +0.64] | -1.29 |
| Exact slot F1 (per-row mean) | 26.22 | 27.32 | +1.10 | [-0.21, +2.48] | [+0.00, +2.25] | +1.10 |
| Official SLU F1 (per-row mean) | 33.14 | 35.02 | +1.88 | [+0.65, +3.17] | [+0.83, +2.93] | +1.88 |

Under projection v3 the intent delta is exactly **0.00 pp** (79.35 both arms), action accuracy is
exactly 0.00 and scenario accuracy is **+0.37** in the arm's favour, while pooled SLU-F1 stays
negative. Both projected views keep the same two-sided pattern as the official one: pooled count F1
down, per-row means up. All three scorings agree in sign on the primary.

## Every scenario, B7a v2 minus the sealed anchor (natural mixture; equal-scenario mean last)

| scenario | n | anchor SLU | B7a v2 SLU | delta | anchor intent | B7a v2 intent | delta | intent CI95 | net harmed | decision-17 flag | loses beyond the band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | --- |
| alarm | 60 | 52.66 | 47.80 | -4.86 | 83.33 | 78.33 | -5.00 | [-14.63, +8.33] | +3 | no | no |
| audio | 60 | 47.75 | 40.50 | -7.25 | 76.67 | 81.67 | +5.00 | [+0.00, +9.68] | -3 | no | no |
| calendar | 60 | 48.38 | 47.17 | -1.21 | 75.00 | 76.67 | +1.67 | [-3.51, +7.84] | -1 | no | no |
| cooking | 60 | 62.47 | 61.88 | -0.59 | 85.00 | 83.33 | -1.67 | [-5.66, +0.00] | +1 | no | no |
| datetime | 60 | 59.52 | 60.74 | +1.22 | 83.33 | 88.33 | +5.00 | [+0.00, +10.45] | -3 | no | no |
| email | 60 | 36.64 | 37.18 | +0.55 | 85.00 | 85.00 | +0.00 | [-6.90, +6.67] | +0 | no | no |
| general | 60 | 15.45 | 13.33 | -2.12 | 36.67 | 31.67 | -5.00 | [-12.96, +1.75] | +3 | no | no |
| iot | 60 | 55.53 | 57.98 | +2.45 | 86.67 | 85.00 | -1.67 | [-5.36, +0.00] | +1 | no | no |
| lists | 60 | 43.55 | 36.78 | -6.76 | 83.33 | 81.67 | -1.67 | [-5.56, +0.00] | +1 | no | no |
| music | 60 | 34.53 | 30.11 | -4.42 | 76.67 | 75.00 | -1.67 | [-8.77, +5.45] | +1 | no | no |
| news | 60 | 44.24 | 40.60 | -3.64 | 80.00 | 78.33 | -1.67 | [-5.77, +0.00] | +1 | no | no |
| play | 60 | 46.82 | 47.00 | +0.17 | 58.33 | 50.00 | -8.33 | [-18.97, +2.04] | **+5** | **FLAG** | no |
| qa | 60 | 57.04 | 54.41 | -2.62 | 75.00 | 76.67 | +1.67 | [+0.00, +4.92] | -1 | no | no |
| recommendation | 60 | 49.75 | 50.67 | +0.93 | 90.00 | 86.67 | -3.33 | [-8.47, +0.00] | +2 | no | no |
| social | 60 | 34.74 | 41.08 | +6.34 | 66.67 | 68.33 | +1.67 | [+0.00, +5.66] | -1 | no | no |
| takeaway | 60 | 48.84 | 53.62 | +4.78 | 85.00 | 85.00 | +0.00 | [-4.48, +5.17] | +0 | no | no |
| transport | 60 | 51.34 | 53.53 | +2.20 | 86.67 | 88.33 | +1.67 | [+0.00, +4.62] | -1 | no | no |
| weather | 60 | 53.81 | 51.59 | -2.22 | 90.00 | 91.67 | +1.67 | [+0.00, +5.66] | -1 | no | no |
| **equal-scenario mean** | 18 x 60 | | | **-0.95** | | | **-0.65** | | | | |

Eight scenarios gain pooled SLU and ten lose it; **no scenario's own intent CI95 upper bound is
below zero**, so conjunct (d) passes. One scenario carries owner decision 17's diagnostic flag:
**`play`, net +5 harmed rows** (0 saves, 5 harms, -8.33 pp intent, CI95 [-18.97, +2.04]). Against
the released direct anchor two scenarios breach the band (`alarm`, `general`) and three carry the
decision-17 flag (`alarm`, `general`, `lists`); that contrast gates nothing. The full tables for
both contrasts, in both weightings and for every metric, are in `per-scenario-tables.json`.

## Node Context Policy receipts, per boundary

5,621 per-contact `saea-node-context-policy-compilation-v1` receipts, one per contact, policy id
`typed-slurp-node-context-v1`, 14,727 `saea-node-context-policy-v1` boundary rows. The anchor
declares no node context policy at all (`node_context_policy_compilations` absent from every one of
its 1,080 receipts). The expectation column is section 3.1 of the v1 preregistration, measured
contact-free on the **anchor's** own 5,417 contacts; this arm flew 5,621 of its own, so the column
is a **comparison and never an equality gate**.

| boundary | rows | structured | parsed | malformed -> FALLBACK-RAW | raw rows | rewritten | median rendered chars | anchor expectation (rows / structured / parsed / FALLBACK-RAW / raw) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `B-CAND-SOL` | 1,136 | 1,136 | 1,136 | 0 | 0 | 1,136 | 325 | 1085 / 1085 / 1085 / 0 / 0 |
| `B-CAND-REV` | 2,272 | 2,272 | 2,272 | 0 | 0 | 2,272 | 325 | 2167 / 2167 / 2167 / 0 / 0 |
| `B-DRAFT-REV` | 2,384 | 2,384 | 2,364 | **20** | 0 | 2,384 | 229 | 2177 / 2177 / 2163 / 14 / 0 |
| `B-DRAFT-PLAN` | 1,187 | 1,187 | 1,177 | **10** | 0 | 1,187 | 480 | 1090 / 1090 / 1083 / 7 / 0 |
| `B-DRAFT-SOL` | 56 | 56 | 55 | **1** | 0 | 56 | 189 | 5 / 5 / 5 / 0 / 0 |
| `B-REVIEW-PLAN` | 2,374 | 1,187 | **0** | **1,187 (100 %)** | 1,187 | 1,187 | 94 | 2177 / 1090 / 0 / 1090 / 1087 |
| `B-REVIEW-SOL` | 112 | 56 | **0** | **56 (100 %)** | 56 | 56 | 226 | 10 / 5 / 0 / 5 / 5 |
| `B-PLAN-SOL` | 56 | 56 | 56 | 0 | 0 | 56 | 96 | 5 / 5 / 5 / 0 / 0 |
| `B-TOOL-REVIEWER` | 1,248 | 0 | 0 | 0 | 1,248 | 0 | 10,377 | 1092 / 0 / 0 / 0 / 1092 |
| `B-TOOL-PLANNER` | 1,187 | 0 | 0 | 0 | 1,187 | 0 | 10,377 | 1087 / 0 / 0 / 0 / 1087 |
| `B-TOOL-SOLVER` | 56 | 0 | 0 | 0 | 56 | 0 | 10,405 | 5 / 0 / 0 / 0 / 5 |
| undeclared (`B-UNDECLARED`) | 2,659 | 0 | 0 | 0 | 2,659 | 0 | 57 | 2202 / 0 / 0 / 0 / 2202 |
| **all boundaries** | **14,727** | **8,334** | **7,060** | **1,274** | **6,393** | **8,334** | | 13,102 / 7,624 / -- / -- / 5,478 |

Every `level: "raw"` row's `rendered_sha256` equals its source's `content_sha256` on **6,393 of
6,393** raw rows: L0 byte identity holds as a checked statement, not an intention. The four
tool-observation boundaries are declared `raw` and none was rewritten.

### Rewritten states per role, against the contact-free expectation

| consumer role | contacts (arm) | agent states | states rewritten | anchor expectation (contacts / states / rewritten) |
| --- | ---: | ---: | ---: | --- |
| perception | 1,080 | 0 | 0 | 1,080 / 0 / 0 |
| solver | 1,136 | 1,416 | 1,304 | 1,085 / 1,110 / 1,100 |
| reviewer | 2,272 | 7,376 | 4,656 | 2,167 / 6,548 / 4,344 |
| planner | 1,133 | 5,935 | 2,374 | 1,085 / 5,444 / 2,180 |

Every role's realised count runs above its expectation in the same proportion as its contact count
(the arm made 204 more contacts than the anchor, +3.8 %, and 59 revisions against the anchor's 6);
Perception is 0 of 0 exactly as predicted, because a Perception contact carries no agent state.

### Reviewer parse rate

**0 parsed of 1,243 structured review-finding rows -- FALLBACK-RAW on 100 % of them**, exactly the
v1 registration's prediction. The Reviewer stays prose on this base; its response format is cell
B7r's factor, not this cell's. On every row the review block therefore reads as the Reviewer's own
bytes under an `UNPARSED` header: **this cell does not structure the review, it declares and
receipts what the review is.**

### The malformed Solver drafts

**9 rows** carried a Solver draft that did not parse at the Planner's current-draft boundary, against
the audit's 7 on the anchor (`B-DRAFT-PLAN` 10 malformed rows over 9 distinct samples;
`B-DRAFT-REV` 20; `B-DRAFT-SOL` 1). On **0 of those 9** does the arm's last Planner action differ
from the anchor's last Planner action on the same row -- both are ACCEPT on all nine. Reported as a
count, never as a claim: the Planner's `HARNESS CHECKS` block flagged the draft on every one of
them and the route did not change.

## Finite completions, and the E8c illegal-action disposition

`terminal_disposition.reason == "finite_completion"` on **3 rows of 1,080**. All three were
**Reviewer** contacts at the **review** stage with `finish_reason` `length`; all three delivered the
**latest delivery-eligible Solver draft** and **none** abstained.

| sample id | interrupted role | stage | finish reason | revision count | delivered | delivered chars |
| --- | --- | --- | --- | ---: | --- | ---: |
| `slurp:train:002333:audio-1488984352` | reviewer | review | length | 0 | latest Solver draft | 121 |
| `slurp:train:004480:audio-1501767977` | reviewer | review | length | 1 | latest Solver draft | 95 |
| `slurp:train:004722:audio-1502896532-headset` | reviewer | review | length | 1 | latest Solver draft | 101 |

By finish reason `{length: 3}`; by role `{reviewer: 3}`; by stage `{review: 3}`; Solver-delivered 3,
abstained 0. **These rows are RETAINED and scored as delivered, and this verdict filters no row.**
Because the count is non-zero, the primary metric is shown beside the same metric with those rows
removed -- a diagnostic, never the decision number:

| population | rows | anchor pooled SLU | B7a v2 pooled SLU | delta | speaker CI95 | intent delta | speaker CI95 |
| --- | ---: | ---: | ---: | ---: | --- | ---: | --- |
| all 1,080 rows (**REGISTERED**) | 1,080 | 48.5336 | 48.2236 | **-0.3100** | [-1.8072, +1.1211] | **-0.6481** | [-2.1849, +0.8688] |
| finite rows excluded (diagnostic) | 1,077 | 48.5253 | 48.2110 | -0.3144 | [-1.8152, +1.1211] | -0.6500 | [-2.1906, +0.8704] |

Three rows carry 0.0044 pp of the primary delta. **The finite-completion policy is what let this
flight finish**: the same event -- one Reviewer completion reaching the 512-token cap -- aborted the
v1 recovery arm at 1,451 contacts on 2026-09-19. It fired three times here and cost 0.004 pp.

`planner_action_illegal` (item E8c, the inherited obligation of the v1 recovery note section 8):
**2 rows**, `slurp:train:002147:audio-1434541391` and `slurp:train:015637:audio-1501754002`, each
with `count: 1` and the same offending action digest
`0db1d699388e290aeb5ddf7c114d3f90120d70de829ee5a85f0748f7112080e8` (the action text is model output
and is not printed here). **Disposition:** the row is retained, delivers its committed draft and
records the marker; it is not a flight abort. Those two rows are in every metric above. The sealed
anchor carries **0** of them.

**The E8c disposition breakdown.** 1,133 Planner routes: **1,072 ACCEPT, 59 REVISE, 2
illegal-action**. Revision histogram `{0: 1,079, 1: 54}`. Three further rows stopped at the
revision limit with a REVISE that had no revision left
(`slurp:train:002929:audio-1501693634-headset`, `slurp:train:010642:audio-1492784427-headset`,
`slurp:train:015846:audio-1501690491`). The sealed anchor's own routes: 1,085 total, 1,079 ACCEPT,
6 REVISE, 0 illegal, 1 revision-limit stop. **The arm revised roughly ten times as often as the
anchor** (59 against 6) -- the single largest behavioural difference this read found, reported
without attribution because eight boundaries move together.

## Per-contact prompt-token volume by role (owner decision 41, throughput root cause)

Read from each arm's own sealed per-request COST records. L1 is a deterministic, zero-contact
transform: it adds prompt volume, not contacts. One table, no analysis.

| role | contacts (arm) | contacts (anchor) | median prompt tokens (arm) | median (anchor) | median delta | p90 (arm) | p90 (anchor) | p90 delta | max (arm) | max (anchor) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| perception | 1,080 | 1,080 | 3,593 | 3,593 | **0** | 3,650 | 3,650 | **0** | 3,756 | 3,756 |
| solver | 1,136 | 1,085 | 9,166 | 8,964 | +202 | 11,017 | 10,706 | +311 | 15,278 | 12,968 |
| reviewer | 2,272 | 2,167 | 10,236 | 9,905 | +331 | 12,578 | 12,062 | +515 | 17,070 | 14,860 |
| planner | 1,133 | 1,085 | 11,302 | 10,804 | +498 | 13,157 | 12,569 | +588 | 17,359 | 14,868 |

Whole-run prompt tokens 49,586,447 against the anchor's 45,998,267 (+3,588,180, +7.80 %); per
contact 8,821.6 against 8,491.5 (+330.1, +3.89 %).

## Cost and duty cycle

| figure | B7a v2 | anchor | direct |
| --- | ---: | ---: | ---: |
| generation contacts | 5,621 | 5,417 | 1,080 |
| contacts per row | 5.205 | 5.016 | 1.000 |
| repeated speech seconds | 16,098.67 | 15,459.76 | 3,084.53 |
| prompt tokens | 49,586,447 | 45,998,267 | 2,459,915 |
| completion tokens | 293,789 | 255,153 | 26,764 |
| native task-contract tool calls | 1,136 | 1,082 | 0 |
| summed request latency (s) | 50,771.0 | 46,114.7 | 1,185.9 |
| GPU active seconds | 13,611.3 | 12,196.6 | 313.5 |
| GPU hours | **3.7809** | 3.3880 | 0.0871 |
| generation wall seconds | 13,930.9 | not in its receipts | 450.6 |
| slot occupancy | 0.911 | not in its receipts | 0.658 |
| mean utilisation (%) | 90.09 | 88.73 | 55.66 |
| parked fraction | 0.022 | 0.022 | 0.281 |
| mean latency (s) | 9.032 | not in its receipts | 1.098 |
| preprocess seconds | 16.71 (8 workers) | not in its receipts | 13.03 |
| official scoring seconds | 204.35 | not in its receipts | 156.42 |
| official scoring jobs | 1 | 1 | 1 |

**Prompt fit.** 5,621 request-fit receipts, 22,484 endpoints, **every request fits**; minimum margin
**6,703 tokens** on the `planner` phase against the 24,576-token slot; widest realised request
**17,873 tokens**. Per phase: perception 1,080 contacts / min margin 20,306; solver 1,136 / 8,784;
reviewer 2,272 / 6,992; planner 1,133 / 6,703. The anchor's own FIT receipts read 5,417 receipts,
21,668 endpoints, minimum margin 9,194 tokens, widest realised request 15,382 -- so L1 consumed
2,491 tokens of the anchor's headroom at the widest point and 2,491 at the minimum margin.

**Registered ceilings, run-cumulative across every attempt of this run id.** v2 is a fresh flight
from row one; the two aborted v1 attempts were charged to their own closed run ids.

| ceiling | registered | actual | headroom |
| --- | ---: | ---: | ---: |
| generation calls | 11,880 | 5,621 | 6,259 |
| repeated speech seconds | 33,930 | 16,098.67 | 17,831.33 |
| fit-inclusive GPU hours | 12.0 | 3.78 | 8.22 |
| native task-contract calls | 6,480 | 1,136 | 5,344 |
| official complete scoring jobs | 1 | 1 | 0 |
| ASR / encoder / paid-API calls | 0 | 0 | 0 |

## Wire evidence

`core.flight.cli wire-check` is unavailable for any native-episode cell, for the reason both v1
packages and the v2 registration record. What stands in its place here is the **first-request
identity check**: the first MODEL_REQUEST of each row is its Perception contact, which carries no
agent state, so the node-context transform has nothing to rewrite and that request is identical by
construction. Every **later** request is not expected to match -- greedy decoding at temperature 0
is not bitwise reproducible across batch compositions, so a divergent predecessor response changes
every request after it.

The compared digest is the whole request payload minus exactly three bookkeeping fields, each named:
`request_id` (the flight counter), every `evidence_provenance` `relpath`
(`rails-message/flight-<n>/k`, the same counter -- each entry's `lock_key` and `sha256` stay
compared), and `decoding_params.id_slot` (which of the resident session's four llama-server KV slots
the scheduler handed the contact). `history`, `task_instruction`, `supplied_evidence`,
`tool_schemas`, `max_tokens`, `response_format`, `parallel_tool_calls`, `speech_feature_parts`,
`speech_packet_sha256`, `speech_ref`, `media_relpath`, `key_representation_id`, `matcher_policy_id`,
`query_source`, `mmproj_loaded`, `sample_rate_hz` and `audio_seconds` are all inside it.

| comparator | rows comparable | model-facing first requests identical | holds on every comparable row |
| --- | ---: | ---: | --- |
| the sealed dual-store anchor | 1,080 | **1,080** | YES |
| the closed v1 recovery arm (only the rows it reached) | 276 | **276** | YES |

**1,080 of 1,080** against the anchor. The v1 recovery attempt aborted partway, so only the 276 rows
it reached are comparable against it; the remainder have no v1 counterpart and are not comparable,
which is not a failure. The v1 recovery trace
(`bb4c214b1b929e9f734abeaa084a832a906ad373c79da79dd857678a823b5dcb`) was streamed **read-only** and
only request digests, sample ids and counters were taken from it -- it was never scored and never
read for quality.

## What is not claimed

- **No superiority, generalization, component-causal or confirmatory claim.** This is a descriptive
  paired read on historically exposed TRAIN Fold A discovery rows; nothing about Fold B, DEV-1000 or
  the test split.
- **No per-boundary attribution.** Eight boundaries move together in this cell. The per-boundary
  receipt table says what each boundary did; it does not say what each boundary cost.
- **No claim that the Node Context Policy is harmful in substance.** The verdict word is the rule's,
  and on this evidence it is produced by interval width against an imported margin, with both point
  estimates inside that margin and every non-width conjunct passing. A cell that measured this
  configuration's own null would decide the question; none is registered, and this read does not
  register one.
- **No claim about the revision-rate difference** (59 REVISE against the anchor's 6), the
  pooled-versus-per-row disagreement, or the `play` scenario's five net harmed rows. All three are
  reported diagnostics.
- **No claim that the finite-completion policy improves anything.** It decides what happens to a
  truncated row; it fired three times and moved the primary by 0.0044 pp.
- **Nothing about task quality from either closed v1 attempt.** They were never scored and never
  read; no partial read was taken here either.

## The harness-admission consequence (a proposal for the coordinator)

This verdict does not write `docs/receipts/harness-admission.json`; the receipt is the coordinator's
to close and `scripts/checks/harness_admission_check.py` is its oracle. Proposed entry:

- **module**: node context policy at level L1 (E8a/E8b: one declared handling policy per node
  boundary; `structured` on the eight model-output boundaries, `on_parse_failure` `raw` everywhere
  except `solver:plan-action` (`refuse`), the four tool-observation boundaries `raw`, no producer
  response format)
- **carrier**: `slurp`
- **class**: `episode`
- **key**: `native_episode.context_policy` (already the third member of
  `rails.config_tables.EPISODE_LEVEL_SWITCH_KEYS`)
- **off**: the key **absent** -- which is what the sealed dual-store anchor carries, and which
  composes to the same behaviour as the pre-policy baseline
- **on**: the L1 block exactly as flown, policy id `typed-slurp-node-context-v1`, as composed into
  `configs/baseline/slurp-native-anchor-ncp-l1-train-fold-a-v2.json`; the flown bytes are pinned by
  composed config `73a817ffda56b02501002685db0cd695516425644544fa040464efb17849d494`
- **comparator**: `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1` /
  `attempt-slurp-native-dual-store-train-fold-a-anchor-generation-recovery-v1`, the sealed dual-store
  anchor; never re-flown or re-scored. It declares no node context policy at all, so the OFF arm is
  the key's absence rather than a null arm of its own.
- **row**: `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-V2`
- **status**: **HARMFUL** -- the table's status for an entry where a gating guard fails; it stays in
  the record as a documented negative and never enters a plan
- **status_basis**: official pooled SLU-F1 48.5336 -> 48.2236, **-0.3100 pp CI95 [-1.8072, +1.1211]**
  (conjunct (a) fails: the lower bound is not above zero); intent 77.9630 -> 77.3148, **-0.6481 pp
  CI95 [-2.1849, +0.8688]** (conjunct (b) fails: the lower bound is below the -1.0051 margin); the
  NEUTRAL test fails on both metrics (SLU -1.8072 < -1.1218). Conjunct (c) passes on all three
  scorings (official -0.3100, projection v3 -0.5029, TRAIN symmetric -0.6752, same sign) and
  conjunct (d) passes (0 of 18 scenarios lose intent beyond the null band). **The failure is one of
  interval width, not of measured loss**: both point estimates are inside the margins, and this
  cell's own CI95 half-widths are 1.4641 (SLU) and 1.5269 (intent) against the borrowed 1.1218 /
  1.0051. Mechanism as declared and as predicted: 14,727 boundary rows on 5,621 contacts, 8,334
  structured and 6,393 raw with byte identity checked on every raw row, **100 % FALLBACK-RAW on all
  1,243 structured review-finding rows**, nine malformed Solver drafts now flagged to the Planner
  with the route unchanged on all nine, and +330 prompt tokens per contact (+3.89 %) for +0.39 GPU
  hours.
- **evidence**: this verdict; the sealed score
  `e824f964b437875ccf2577be74ef57cc334a9ffbb79558a84cc827996c6de9dc`; the run manifest
  `eb4714371aa95dedf13dfbaabb943e0b68d13b1a8e05ecd944a5c6b23db0a343`; the paired read
  `SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-B7A-NCP-L1-ANCHOR-V2-PAIRED-ANALYSIS-V1/` with
  `score-contrasts.json` `0245349f99cf37a0132bfa78c588ed406ff73ecae934504cb330f0dd6e84f8be` and
  every other output hashed in its `README.md`
- **caveats**: the margins are imported from cell B0r's review-off geometry and are narrower than
  this cell's own measured half-widths; the two per-row means (exact slot F1 +1.33, per-row SLU-F1
  +1.98) both have CI95 lower bounds above zero while the pooled primary is negative; the arm
  revised 59 times against the anchor's 6; one scenario (`play`) carries owner decision 17's net-5
  flag.
- **not_admitted_for**: any default plan; and, per the rule's own consequence, **cell B7b (level L2)
  is not flown**.

**One point the coordinator may wish to record.** Three SLURP cells have now been closed by the
imported B0r margins rather than by a measured loss (B0 review-off, B5e, and this one), while the
one cell that measured its own null found it wider (B4b-rep: h_SLU 1.3222, h_intent 1.0682). This
cell's half-widths are wider still. Whether the review-on five-contact geometry should keep
borrowing 1.1218 / 1.0051 is a program question this verdict does not decide.

## Exposure-ledger closure inputs (the coordinator edits the ledger; this read does not)

Two rows of `docs/exposure-ledger.md` are open at `consumed = yes` with planned figures:

| row | registered | actual |
| --- | --- | --- |
| `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-V2` | 11,880 calls / 33,930 speech seconds | **5,621 calls / 16,098.666250 speech seconds**; 5,621 request-fit receipts, all fitting; 1,136 native task-contract tool calls; 3.7809 GPU hours from the serving monitor; one official complete scoring job; 0 ASR, encoder and paid-API calls |
| `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-FIT-V2` | 47,520 endpoints / 33,930 speech seconds | **22,484 endpoints over 5,621 receipts** under `SPEECHRL_DATA_DIR/prepared/SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-FIT-V2/attempt-slurp-native-ncp-l1-anchor-train-fold-a-fit-v2/`; model-free |

Attempt state FINALIZED; `SPEECHRL_DATA_DIR/attempts/SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-V2/`
holds exactly one attempt file, reserving 11,880 calls / 33,930 seconds and recording 5,621 /
16,098.666250 actual.

## Artefacts

Analysis root `SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-B7A-NCP-L1-ANCHOR-V2-PAIRED-ANALYSIS-V1/`, the
path the recipe's `output.analysis_root` names.

| file | SHA-256 |
| --- | --- |
| `score-contrasts.json` | `0245349f99cf37a0132bfa78c588ed406ff73ecae934504cb330f0dd6e84f8be` |
| `README.md` | `7db9a7c9d764a000267de0c66c789ced2c939a7ef4117f9d90231a7773d7b3bc` |
| `per-scenario-tables.json` | `0a8bb6a977cb388304ef5e420b13ae90373cab20b7da7818c533c98cbd27ca38` |
| `flight-diagnostics.json` | `447955670fafa325ea92c1b4faef58778b75f2dfd8f7141107ffd251cb5b68cc` |
| `b7a2_paired_read.py` (the driver, copied into the package) | `d8af2e7be48ff589089317cf6f7100d50537be56c12d95d16cf2e221abd49544` |

Every input and output of the read -- sealed scores, manifests, outputs, phase artefacts, traces,
flight receipts, generation manifests, roster, roster metadata, the eleven authority documents and
the ten estimator implementations -- is hashed in `score-contrasts.json` under `inputs` and
`outputs`, and the projection-v3 / symmetric score files and the outputs copies are hashed there too.

**Two registered paths differ between the recipe and the task brief, and the recipe wins:** the
analysis root is `SAEA-SLURP-B7A-NCP-L1-ANCHOR-V2-PAIRED-ANALYSIS-V1` (not
`SAEA-SLURP-B7A-V2-PAIRED-ANALYSIS-V1`) and this verdict is
`docs/results/2026-09-19-slurp-b7a-ncp-l1-anchor-v2-verdict.md` (not
`docs/results/2026-09-19-slurp-b7a-v2-verdict.md`). The brief's extra deliverable
`per-scenario-tables.json` was written as well, beside the recipe's two named files.

## Exposure

**Zero model, tokenizer, encoder, ASR and server contacts.** Execution profile `model-free-check`.
The only scorer invocations are the model-free projection-v3 and TRAIN symmetric scorings, three
arms each, every one over a COPY of that arm's sealed `outputs.jsonl` written under the analysis
root. No sealed file was opened for writing, moved or renamed; nothing was written under
`SPEECHRL_DATA_DIR/runs` or `SPEECHRL_DATA_DIR/attempts`; no serving session, flight worktree,
scheduled task or flight lock was touched; no exposure-ledger row, harness-admission receipt,
results ledger or readiness document was edited. No utterance text, transcript, gold filler or model
output was printed or persisted: this read reports counts, aggregate numbers, scenario names, sample
ids and content hashes only, and the two illegal Planner actions are identified by SHA-256 rather
than by their text.
