# HARMFUL -- cell B4a (standing `general_quirky` fallback + intent-boundaries v2) on the sealed dual-store anchor, SLURP TRAIN A

Status: **HARMFUL**, the word the registered decision rule names. Against the sealed dual-store
anchor on the same 1,080 TRAIN Fold A rows the **primary** metric, intent (joint scenario+action)
accuracy, is **+0.7407 pp, CI95 [-0.3031, +1.7544]**, and the **gating guard**, official pooled SLU
micro F1, is **-0.7049 pp, CI95 [-2.2930, +0.8861]**. Conjunct (a) fails, because the intent CI95
lower bound is not above zero. The HARMFUL branch then fires on its **second** clause: the pooled
SLU CI95 lower bound **-2.2930 is at or below the -1.1218 pp own-null margin**. Conjuncts (c) and
(d) both pass. The rule's stated consequence is that cell B4a **does not enter the SLURP default
plan**, and owner decision 9 of 2026-09-17 conditions cell **B4c on cell B4a ADMITTING**, so
**B4c is not flown**.

**The verdict is driven by interval width, not by a measured loss.** The pooled SLU point estimate
-0.7049 sits inside the 1.1218 pp margin it must clear; what fails is that this cell's own CI95
half-width for pooled SLU is **1.5895 pp**, 41.7 % wider than the B0r review-off value the rule
borrows. This is the fourth SLURP cell closed that way (B0 review-off, B5e, B7a v2, and this one).
The verdict records the fact; it does not change the rule or the status.

**The cell's own target did not move at all, and the mechanism says why.** The appended fallback
candidate reached the Solver on **1,052 of 1,080 rows** and raised candidate coverage on the gold
`general_quirky` rows from 24.44 % to **100 %** -- and the frozen core selected it on **zero** of
those 1,052 rows. `general` scenario intent is **36.67 % on both arms**, exactly the A3 baseline;
`qa` intent is **75.00 % on both arms**, with 0 saves and 0 harms. What did move is the covariate
the preregistration named: the Solver's slot-card supply grew by a median of **8 extra cards per
row** (12 -> 20), prompt volume grew **+29.96 %**, GPU hours **+39.35 %**, and the two slot-level
readings fell (pooled span F1 -2.00 pp, per-row exact slot F1 -1.91 pp with 60 harms against 35
saves, McNemar p 0.013).

Date: 2026-09-19. Root: Claude Opus 5 (1M). Read once, from the single official score of the
complete manifest. Execution profile `model-free-check`; zero model, tokenizer, encoder, ASR and
server contacts.

## What flew

| field | value |
| --- | --- |
| run | `SAEA-SLURP-NATIVE-FALLBACK-QUIRKY-INTENT-V2-ANCHOR-TRAIN-FOLD-A-V2` |
| attempt | `attempt-slurp-native-fallback-quirky-intent-v2-anchor-train-fold-a-generation-v2`, FINALIZED |
| manifest | `COMPLETED` at study commit `682ee52de786bcec0efde74ba04b97f4eeec6e57`, `study_repo_dirt` empty |
| composed config | `a07e895cf893bf2a8ba348449e949f3b0db18808d4435a3670ef49fa37f452d2` -- the registered value |
| protocol | `2577e3c90ab1ac7b90819926ae931fb008dc92f0aaaa26e44917dd55135702ee` -- the registered value |
| run manifest SHA-256 | `fa93e14923e8192e9426a024792073cf606d9303334d208d68cfd208f02d1036` |
| official score SHA-256 | `633601d1350c4775d63b0ba31fef038370f4615f9ca46b99e58466ad2c34f016` |
| outputs SHA-256 | `eb8044e386094d93934e6152e66695434eeb8bdd59fd3790117d819597e5e3ff` |
| rows | 1,080 distinct, split identity `61b0f0625497...5398b`, role `discovery`, 125 speaker clusters, 18 scenarios of 60, 523 headset / 557 far-field |
| scoring | one official complete job, `slurp-slu-official-train`, evaluator `slurp-official-8eb16545`, split `train`, port/official identity check passed, `projection.applied` false |

**The one moved factor, both halves.** `knowledge_stores.slot-contracts.candidate_supply.solver.
fallback_candidates = ["general_quirky"]` with its mirrored
`phase_material.perception.fill_params.fallback_candidates`, and `knowledge_stores.intent-boundaries`
re-pinned from v1 (release `2e51c14b…`, snapshot `5520b844…`) to v2 (release `31eb595b…`, snapshot
`8a27424a…`). Everything else -- roster, split, model fragment, resident geometry, speech packets,
the full native episode with the review loop on, the Reviewer-only task-contract authority, the
candidate contract, the Perception retrieval geometry, every instruction template and the scorers --
is the anchor's. The slot-contracts store stays at v1 on both arms.

**Both arms are NODE-FREE**: this cell and the sealed anchor were both registered before module M3,
the delivery normaliser, entered the default plan. Both were flown with **per-role tool rendering**
(the anchor's own live `phase_tools` block), so the Reviewer's task-contract authority is reachable
on both. The arm carries the **finite-completion policy** (`deliver-latest-or-abstain`, a harness
declaration, not a factor) and the anchor does not;
`docs/receipts/slurp-finite-completion-exposure-v1.json` proves the anchor met zero finite
completions over its 5,417 contacts, and **this arm met zero as well**, so the declaration changed
no delivered byte on either side.

## The STOP conditions, closed before any B4a table was read

1. **Both sealed comparator aggregates reproduced from their own bytes.** The dual-store anchor's
   official 48.53 / 77.96 / 84.81 / 79.26 / 29.50 and the released direct anchor's 33.89 / 73.70 /
   82.69 / 75.09 / 21.10, each recomputed with `analysis.null_calibration.pooled_f1` and
   `analysis.null_calibration_cli.rows_for` and matched to the registered value.
2. **Pooled recomputation matches every arm's own official aggregate to 1e-6**, for pooled SLU and
   pooled span, on all three arms.
3. **The anchor's candidate sets were re-derived and cross-checked against the sealed A3 audit.**
   This read parses each anchor row's Perception state with the registered
   `rails.slurp_intent_hypotheses` parser and compares the result to
   `analysis/SAEA-SLURP-A3-COVERAGE-CONFUSION-AUDIT-V1/join-v1.json`
   (SHA-256 `37f61c5f84164ef5c4165767a6274fc8fc458500dfb3ab6ef5c28371e9d8d9cf`):
   **1,080 / 1,080 candidate sets and 1,080 / 1,080 gold intents reproduced.**
4. **The arm's own selection audits bind to its own Perception states.** Each row's
   `saea-candidate-semantic-selection-v1` audit declares `fallback_candidates ["general_quirky"]`,
   and its `candidate_ids_without_fallback` equals the registered parse of that row's **last**
   Perception visit on **1,080 / 1,080 rows** (4 rows carry two Solver supplies).
5. **The delivered parse matches the official score row by row.** `parse_slu_response` reproduces
   the official `parsed` flag and the `scenario_action_exact` outcome on all 1,080 rows of both
   arms; no coverage or confusion number was read before that held.

## (a) B4a minus the sealed dual-store anchor -- the PRIMARY contrast (percentage points)

Paired whole-speaker cluster bootstrap, 125 clusters, 10,000 draws, seed 20260915; CI95 for
advancement, CI90 for diagnostics, both percentiles of the same retained replicate sequence.
Sensitivity: paired scenario-stratified row bootstrap, same draws and seed.

| metric | estimand | anchor | B4a | delta | speaker CI95 | speaker CI90 | CI95 half-width | stratified CI90 | equal-scenario |
| --- | --- | ---: | ---: | ---: | --- | --- | ---: | --- | ---: |
| **Intent (scenario+action)** -- PRIMARY | mean per row | 77.9630 | 78.7037 | **+0.7407** | **[-0.3031, +1.7544]** | [-0.1026, +1.5842] | 1.0287 | [-0.3704, +1.8519] | +0.7407 |
| **Official pooled SLU micro F1** -- GATE | pooled count F1 | 48.5336 | 47.8287 | **-0.7049** | **[-2.2930, +0.8861]** | [-2.0233, +0.6193] | 1.5895 | [-1.9676, +0.5877] | -0.2702 |
| Scenario accuracy | mean per row | 84.8148 | 85.4630 | +0.6481 | [-0.2355, +1.5444] | [-0.0953, +1.3931] | 0.8900 | [-0.2778, +1.5741] | +0.6481 |
| Action accuracy | mean per row | 79.2593 | 80.0926 | +0.8333 | [-0.2812, +1.8430] | [-0.0935, +1.6889] | 1.0621 | [-0.2778, +1.9444] | +0.8333 |
| Official span F1 (pooled) | pooled count F1 | 29.4976 | 27.4986 | -1.9989 | [-4.1802, +0.1536] | [-3.8341, -0.1757] | 2.1669 | [-3.8080, -0.2430] | -1.3646 |
| Exact slot F1 (per-row mean) | mean per row | 19.0225 | 17.1116 | -1.9109 | [-3.2718, -0.5350] | [-3.0587, -0.7453] | 1.3684 | [-3.0357, -0.7768] | -1.9109 |
| Official SLU F1 (per-row mean) | mean per row | 30.2940 | 29.0397 | -1.2543 | [-2.5014, +0.0373] | [-2.3069, -0.1788] | 1.2693 | [-2.3279, -0.1804] | -1.2543 |

| per-row metric | saves | harms | ties | exact two-sided McNemar p |
| --- | ---: | ---: | ---: | --- |
| intent (scenario+action) | 30 | 22 | 1,028 | 0.332 |
| scenario | 22 | 15 | 1,043 | 0.324 |
| action | 32 | 23 | 1,025 | 0.281 |
| exact slot F1 | 35 | 60 | 985 | **0.013** |
| per-row SLU F1 | 77 | 94 | 909 | 0.221 |

## (b) B4a minus the released direct anchor (secondary, never a gate)

| metric | direct | B4a | delta | speaker CI95 | equal-scenario |
| --- | ---: | ---: | ---: | --- | ---: |
| Official pooled SLU micro F1 | 33.8851 | 47.8287 | +13.9436 | [+11.0233, +16.9714] | +12.8281 |
| Intent (scenario+action) | 73.7037 | 78.7037 | +5.0000 | [+2.9285, +7.1024] | +5.0000 |
| Scenario accuracy | 82.6852 | 85.4630 | +2.7778 | [+0.6097, +5.0865] | +2.7778 |

The system-over-direct column is unchanged in direction and size; the cell neither adds to nor
subtracts from what the agent system already buys over a single direct contact.

## The rule, applied unchanged

Quoted from `docs/readiness/2026-09-17-slurp-b4-org-cells-anchor-v2/b4a-analysis-recipe-v1.json`
`decision_rule`, identical to section 6 of the preregistration ("B4a, explicitly different"), fixed
before contact:

> **ADMITTED** if the CI95 lower bound of the intent delta against the sealed anchor is greater than
> 0, pooled official SLU micro F1 is non-inferior within 1.1218 pp, the projection-v3 reading agrees
> in sign, and no scenario loses intent beyond the null band. **HARMFUL** if the CI95 lower bound of
> the intent delta is at or below -1.0051 pp, or of the pooled SLU delta at or below -1.1218 pp, or
> a scenario loses intent beyond the null band. **NEUTRAL** if no gate is breached but the CI95
> lower bound of the intent delta is not above 0; the module enters the default plan only if it
> lowers cost, it does not here, so NEUTRAL means not adopted.

| conjunct | test | value | passes |
| --- | --- | --- | --- |
| (a) primary | intent CI95 lower bound > 0 | **-0.3031** | **no** |
| (b) guard | pooled SLU CI95 lower bound > -1.1218 | **-2.2930** | **no** |
| (c) agreement | projection v3 agrees in sign on the primary | official +0.7407, v3 +0.2778 | yes |
| (d) band | no scenario's intent CI95 upper bound below zero | 0 of 18 | yes |

| HARMFUL clause | value | margin | fires |
| --- | --- | --- | --- |
| intent CI95 lower at or below the margin | -0.3031 | -1.0051 | no |
| **pooled SLU CI95 lower at or below the margin** | **-2.2930** | **-1.1218** | **yes** |
| a scenario loses intent beyond the null band | 0 scenarios | -- | no |

The HARMFUL branch fires on the SLU clause alone. Owner decision 25 of 2026-09-16 -- a combination
cell called HARMFUL needs a **measured** loss rather than an interval width -- scopes to
**combination** cells (the B5e addendum of 2026-09-18); cell B4a is a single-factor cell, so its
registered three-way rule reads exactly as written. This verdict nonetheless records that the
measured loss is **-0.7049 pp**, inside the margin, and that the failure is the interval:

| metric | this cell's CI95 half-width | the borrowed B0r margin | ratio |
| --- | ---: | ---: | ---: |
| pooled SLU micro F1 | 1.5895 | 1.1218 | 1.42 |
| intent (scenario+action) | 1.0287 | 1.0051 | 1.02 |

The intent half-width is essentially the borrowed one; the SLU half-width is not. The one cell that
measured its own null on this geometry (B4b-rep, 2026-09-18) found h_SLU 1.3222 / h_intent 1.0682,
also wider than 1.1218 / 1.0051. Whether the review-on five-contact geometry should keep borrowing
the review-off margins is a program question this verdict does not decide.

## Projection v3 and the TRAIN symmetric view, beside the rule

Both are model-free scorings over **copies** of each arm's sealed `outputs.jsonl`, written under the
analysis root; no sealed byte was rewritten. Owner decision 23 of 2026-09-18 keeps the decision
number official and unprojected, and owner decision 28 makes both of these development diagnostics.

| arm | official SLU | v3 SLU | v3 intent | v3 scenario | v3 action | v3 span | rows projected | ineligible |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| anchor | 48.5336 | 51.9946 | 79.3519 | 85.4630 | 80.6481 | 40.3025 | 20 | 7 |
| **B4a** | 47.8287 | 51.6304 | 79.6296 | 86.1111 | 80.9259 | 39.3153 | 21 | 5 |
| direct | 33.8851 | 34.3137 | 75.3704 | 84.1667 | 75.9259 | 23.2359 | 47 | 0 |

The anchor's and the direct anchor's v3 readings reproduce their registered values (51.99 / 79.35 /
85.46 / 80.65 / 40.30 and 34.31 / 75.37 / 84.17 / 75.93 / 23.24) to the last digit.

| reading | intent delta | speaker CI95 | pooled SLU delta | speaker CI95 |
| --- | ---: | --- | ---: | --- |
| official (unprojected) | +0.7407 | [-0.3031, +1.7544] | -0.7049 | [-2.2930, +0.8861] |
| projection v3 | +0.2778 | [-0.7073, +1.2566] | -0.3642 | [-2.0455, +1.3228] |
| TRAIN symmetric | +0.7407 | [-0.3031, +1.7544] | -0.4169 | [-2.0821, +1.2401] |

All three agree in sign on both metrics. The TRAIN symmetric aggregate is 51.6718 (arm) against
52.0887 (anchor), span 40.5301 against 41.3830, with 34 false merges on every arm.

**A recorded deviation.** The recipe states that the symmetric-normalised clause is not evaluable on
this roster because `slurp-slu-f1-normalized-v1` resolves gold from the SLURP `devel` split, and it
substitutes the projection-v3 clause. That statement is **stale in one detail**: the TRAIN sibling
`slurp-slu-f1-normalized-v1-train` resolves in `core.base.SCORERS` and the sealed B4b-rep read of
2026-09-18 used it. Both readings are computed here; the conjunct stays projection v3, as the recipe
fixes it, and the two agree.

## Every scenario, B4a minus the sealed anchor (natural mixture; equal-scenario mean last)

Candidate coverage is the gold intent's presence in the candidate list the delivering Solver was
supplied for -- "model" is the core's own three projected candidates, "+fb" is after the standing
fallback was appended.

| scenario | n | anchor SLU | B4a SLU | dSLU | anchor intent | B4a intent | dIntent | intent CI95 | net harmed | anchor cov | B4a cov (model) | B4a cov (+fb) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| alarm | 60 | 52.66 | 50.42 | -2.24 | 83.33 | 85.00 | +1.67 | [-4.08, +8.70] | -1 | 96.7 | 95.0 | 95.0 |
| audio | 60 | 47.75 | 55.29 | +7.54 | 76.67 | 78.33 | +1.67 | [+0.00, +2.83] | -1 | 91.7 | 91.7 | 91.7 |
| calendar | 60 | 48.38 | 46.18 | -2.20 | 75.00 | 73.33 | -1.67 | [-7.02, +3.77] | +1 | 81.7 | 80.0 | 80.0 |
| cooking | 60 | 62.47 | 63.11 | +0.64 | 85.00 | 85.00 | +0.00 | [-4.69, +4.84] | +0 | 91.7 | 91.7 | 91.7 |
| datetime | 60 | 59.52 | 57.55 | -1.97 | 83.33 | 88.33 | +5.00 | [+0.00, +10.45] | -3 | 95.0 | 96.7 | 96.7 |
| email | 60 | 36.64 | 42.99 | +6.36 | 85.00 | 88.33 | +3.33 | [+0.00, +8.47] | -2 | 88.3 | 90.0 | 90.0 |
| **general** | 60 | 15.45 | 17.02 | +1.57 | **36.67** | **36.67** | **+0.00** | [-8.45, +7.58] | +0 | **43.3** | **40.0** | **100.0** |
| iot | 60 | 55.53 | 60.76 | +5.22 | 86.67 | 85.00 | -1.67 | [-5.08, +0.00] | +1 | 95.0 | 95.0 | 95.0 |
| lists | 60 | 43.55 | 42.66 | -0.89 | 83.33 | 81.67 | -1.67 | [-5.56, +0.00] | +1 | 85.0 | 85.0 | 85.0 |
| music | 60 | 34.53 | 33.87 | -0.67 | 76.67 | 78.33 | +1.67 | [-3.70, +7.41] | -1 | 86.7 | 88.3 | 88.3 |
| news | 60 | 44.24 | 36.69 | -7.56 | 80.00 | 80.00 | +0.00 | [-4.92, +4.92] | +0 | 83.3 | 86.7 | 86.7 |
| play | 60 | 46.82 | 48.66 | +1.84 | 58.33 | 61.67 | +3.33 | [-7.27, +13.79] | -2 | 88.3 | 88.3 | 88.3 |
| **qa** | 60 | 57.04 | 54.55 | -2.49 | **75.00** | **75.00** | **+0.00** | [+0.00, +0.00] | +0 | 78.3 | 78.3 | 78.3 |
| recommendation | 60 | 49.75 | 46.51 | -3.24 | 90.00 | 90.00 | +0.00 | [-4.92, +4.92] | +0 | 95.0 | 95.0 | 95.0 |
| social | 60 | 34.74 | 42.09 | +7.35 | 66.67 | 66.67 | +0.00 | [+0.00, +0.00] | +0 | 81.7 | 81.7 | 81.7 |
| takeaway | 60 | 48.84 | 45.55 | -3.29 | 85.00 | 83.33 | -1.67 | [-5.00, +0.00] | +1 | 91.7 | 91.7 | 91.7 |
| transport | 60 | 51.34 | 48.92 | -2.42 | 86.67 | 88.33 | +1.67 | [+0.00, +5.88] | -1 | 95.0 | 95.0 | 95.0 |
| weather | 60 | 53.81 | 45.38 | -8.43 | 90.00 | 91.67 | +1.67 | [-3.33, +7.69] | -1 | 93.3 | 93.3 | 93.3 |
| **equal-scenario mean** | 18 | | | **-0.27** | | | **+0.74** | | | | | |

**No scenario loses intent beyond the null band** (0 of 18 have a CI95 upper bound below zero) and
**no scenario carries owner decision 17's net-5 flag** (worst net harm +1, on four scenarios). The
intent movement is spread over `datetime` (+5.00), `email` and `play` (+3.33 each) against
`calendar`, `iot`, `lists` and `takeaway` (-1.67 each) -- none of them the scenario the cell
targets. The SLU movement is larger in both directions: `audio` +7.54 and `social` +7.35 against
`weather` -8.43 and `news` -7.56.

## The cell's own target: coverage, the fallback and the qa/general confusion

### Candidate coverage -- the fix landed exactly as designed

| population | rows | anchor | B4a, model's own candidates | B4a, with the fallback | A3 baseline |
| --- | ---: | ---: | ---: | ---: | ---: |
| all rows | 1,080 | 86.76 % (937) | 86.85 % (938) | **90.19 % (974)** | 86.8 % |
| `general` scenario | 60 | 43.33 % (26) | 40.00 % (24) | **100.00 % (60)** | 43 % |
| gold `general_quirky` rows | 45 | 24.44 % (11) | 20.00 % (9) | **100.00 % (45)** | -- |

The anchor's 86.76 % and 43.33 % reproduce the A3 audit's 86.8 % and 43 %. The standing fallback did
exactly what FIX-1 specified: it closed the coverage hole on every gold `general_quirky` row.

### The fallback was appended, and then never chosen

| figure | value | registered expectation (measured on the anchor's distribution) |
| --- | ---: | ---: |
| rows where the fallback was appended | **1,052** | 1,063 |
| rows where the core already proposed `general_quirky` | 28 | 17 |
| **appended rows that then delivered `general_quirky`** | **0 (0.00 %)** | not predicted |
| appended rows whose gold is `general_quirky` | 36 | -- |
| of those, rows the arm got right | **0** | -- |
| rows delivering `general_quirky` at all | 15 (anchor 11) | -- |
| of those, rows where the core proposed it itself | **15 of 15** | -- |

Every row on which cell B4a delivered `general_quirky` is a row on which the core's own Perception
response had already proposed it. The appended candidate -- present on 1,052 of 1,080 requests,
carrying 16 bound slot cards -- was selected **zero** times. On this base the fallback's fixed
`DEFAULT_FALLBACK_DISTINCTION` text reaches no request (preregistration section 3.2, correction 3),
so the candidate arrives in the Solver's supply as extra slot cards and as nothing the model is
asked to consider by name.

### The A3 fix cohorts, row for row

| cohort | rows | A3 ceiling | anchor correct | B4a covered | B4a correct |
| --- | ---: | ---: | ---: | ---: | ---: |
| FIX-1: gold `general_quirky`, gold never in the anchor's candidate set | 34 | 34 | 0 | **34** | **2** |
| FIX-2: gold `general_quirky` delivered by the anchor as a `qa_*` id | 11 | 11 | 0 | -- | **2** (9 still `qa_*`) |

Both cohorts reproduce the A3 audit's counts exactly. The two FIX-1 rows the arm gets right are rows
where the arm's **own** Perception proposed `general_quirky` (the fallback was not their source), so
they are decoding variation on a different flight, not the fix firing.

### The qa / general confusion

| figure | anchor | B4a | delta | A3 baseline |
| --- | ---: | ---: | ---: | ---: |
| gold `general_quirky` rows | 45 | 45 | 0 | -- |
| gold `general_quirky` delivered as a `qa_*` id (FIX-2's target) | 11 | 10 | **-1** | 11 |
| gold `qa_*` delivered as `general_quirky` (the reverse direction) | 0 | 1 | **+1** | 0 |
| rows delivering `general_quirky` | 11 | 15 | +4 | -- |
| `general_quirky` true positives | 7 | 8 | +1 | -- |
| `general_quirky` recall | 15.56 % | 17.78 % | +2.22 pp | -- |
| `general_quirky` precision | 63.64 % | 53.33 % | **-10.30 pp** | -- |

The one-directional contrast the revised intent cards carry moved one row off `qa_*` and introduced
one row in the reverse direction, which the A3 audit had at zero. `general` intent is unchanged
(4 saves, 4 harms, 52 ties); `qa` intent is unchanged with **zero** saves and **zero** harms on all
60 rows.

### The named covariate, measured on the arm's own rows

| figure | B4a realized | preregistration section 3.2 (anchor distribution) |
| --- | ---: | ---: |
| slot-card values supplied to the Solver, median | **20** (mean 20.49, min 16, max 27) | 20 |
| of those, values the appended fallback pulled in, median | **8** (mean 8.81, max 15) | 8 |
| the model's own candidates' values, median | 12 | 12 |
| rows at the 28-value total cap | **0** | displacement measured at 0 |

The covariate landed exactly where it was predicted. No row reached the `max_total_values` cap, so
the fallback displaced nothing; it added. This is the only channel of the cell that demonstrably
reached the frozen core, and the two slot-level readings moved against it: pooled span F1 -2.00 pp
and per-row exact slot F1 -1.91 pp with 60 harms against 35 saves (p 0.013). This verdict records
the association and claims no cause: the cell moves the fallback and the intent store together, and
cell B4c is the instrument that would separate them.

## Flight dispositions

| figure | B4a | anchor |
| --- | ---: | ---: |
| finite-completion rows | **0** | 0 (proven by the exposure receipt) |
| illegal Planner actions (E8c) | **0** | 0 |
| revision-limit stops | 0 | 1 |
| Planner routes | ACCEPT 1,080 / REVISE 4 | ACCEPT 1,079 / REVISE 6 |
| revision-count histogram | 0 -> 1,080, 1 -> 4 | 0 -> 1,080, 1 -> 5 |
| role contacts | perception 1,080, solver 1,084, reviewer 2,164, planner 1,084 | 1,080 / 1,085 / 2,167 / 1,085 |

The arm revised **4** times against the anchor's **6**. Because the flight met no finite completion
and no illegal Planner action, there is nothing to exclude and the registered all-rows primary
number stands alone; no row was filtered.

## First model-facing request identity

**Expected: not identical, and it is not.** The whole model-facing digest of each row's first
request differs on all 1,080 rows -- but for one reason that never reaches the model. A per-field
comparison isolates it:

| request field | rows compared | identical | differing |
| --- | ---: | ---: | ---: |
| `supplied_evidence` (whole traced object) | 1,080 | 0 | 1,080 |
| `supplied_evidence` -> `source_uri` only | 1,080 | **0** | **1,080** |
| `supplied_evidence` -> `evidence_id` list only | 1,080 | **1,080** | 0 |
| **`supplied_evidence` -> the wire rendering** | 1,080 | **701** | **379** |
| `evidence_provenance` content (`lock_key` + `sha256`) | 1,080 | **701** | **379** |
| `history` | 1,080 | 1,080 | 0 |
| `task_instruction` | 1,080 | 1,080 | 0 |
| `tool_schemas` | 1,080 | 1,080 | 0 |
| `decoding_params` (minus `id_slot`) | 1,080 | 1,080 | 0 |
| `speech_packet_sha256`, `speech_ref`, `speech_feature_parts`, `media_relpath`, `audio_seconds`, `sample_rate_hz`, `mmproj_loaded`, `query_source`, `key_representation_id`, `matcher_policy_id`, `carrier_lock_key`, `sample_id` | 1,080 | 1,080 | 0 |

`core.model.transport` renders each supplied-evidence item as `[evidence <evidence_id>] <content>`
and **never sends `source_uri`**, which is the one field that embeds the composite
knowledge-snapshot digest -- `54219cf9…` on the arm against `4e74d0d7…` on the anchor -- and
therefore differs on every contact by construction. On the reading the frozen core actually
receives, the first request is **byte-identical on 701 rows and differs on 379**, which is exactly
the registered request-channel proof's 701 / 379 (`request-channel-proof-v1.json`,
`3598de1a…`), now confirmed on the arm's own flown bytes rather than by substitution. The
evidence-id list is identical on all 1,080 rows, so the selected facet ids are the anchor's on every
row, as `phase-supply-vs-anchor-v1.json` promised.

Excluded bookkeeping fields, named and nothing else: `request_id` (the flight counter), every
`evidence_provenance` relpath (`rails-message/flight-<n>/k`, the same counter -- each entry's
`lock_key` and `sha256` stay compared) and `decoding_params.id_slot`. Every later request is
unconstrained in any case: greedy decoding at temperature 0 is not bitwise reproducible across batch
compositions.

## Per-contact prompt-token volume by role (owner decision 41, throughput root cause)

Read from each arm's own sealed per-request COST records. One table, no analysis.

| role | contacts (arm) | contacts (anchor) | median prompt tokens (arm) | median (anchor) | median delta | p90 (arm) | p90 (anchor) | p90 delta | max (arm) | max (anchor) | total (arm) | total (anchor) | total delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| perception | 1,080 | 1,080 | 3,617 | 3,593 | **+24** | 3,737 | 3,650 | +87 | 4,012 | 3,756 | 3,926,127 | 3,884,813 | +41,314 |
| solver | 1,084 | 1,085 | 11,938 | 8,964 | **+2,974** | 12,759 | 10,706 | +2,054 | 15,490 | 12,968 | 12,933,510 | 9,492,410 | +3,441,100 |
| reviewer | 2,164 | 2,167 | 12,921 | 9,905 | **+3,016** | 14,311 | 12,062 | +2,249 | 17,368 | 14,860 | 27,973,464 | 21,112,471 | +6,860,993 |
| planner | 1,084 | 1,085 | 13,788 | 10,804 | **+2,984** | 14,629 | 12,569 | +2,060 | 17,372 | 14,868 | 14,944,110 | 11,508,573 | +3,435,537 |
| **all roles** | 5,412 | 5,417 | | | | | | | | | **59,777,211** | **45,998,267** | **+13,778,944** |

Whole-run prompt tokens 59,777,211 against 45,998,267 (**+29.96 %**); per contact 11,045.3 against
8,491.5 (+2,553.8, +30.08 %).

### Prefill accounting from the server's own usage records

The sealed wire responses carry `usage.prompt_tokens_details.cached_tokens` and `timings.prompt_n`,
so the prefilled share is measured rather than estimated. Every one of the 5,412 and 5,417 contacts
carries a usage record. One table, no analysis.

| role | prompt tokens (arm) | cached (arm) | newly prefilled (arm) | cached share (arm) | prompt tokens (anchor) | cached (anchor) | newly prefilled (anchor) | cached share (anchor) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| perception | 3,926,127 | 2,407,662 | 1,518,465 | 61.3 % | 3,884,813 | 2,394,100 | 1,490,713 | 61.6 % |
| solver | 12,933,510 | 3,720,517 | 9,212,993 | 28.8 % | 9,492,410 | 3,676,507 | 5,815,903 | 38.7 % |
| reviewer | 27,973,464 | 15,431,778 | 12,541,686 | 55.2 % | 21,112,471 | 12,009,963 | 9,102,508 | 56.9 % |
| planner | 14,944,110 | 2,406,480 | 12,537,630 | 16.1 % | 11,508,573 | 2,408,700 | 9,099,873 | 20.9 % |
| **all roles** | **59,777,211** | **23,966,437** | **35,810,774** | **40.1 %** | **45,998,267** | **20,489,270** | **25,508,997** | **44.5 %** |

Newly prefilled tokens +10,301,777 (+40.4 %).

## Cost and duty cycle

| figure | B4a | anchor | direct |
| --- | ---: | ---: | ---: |
| generation contacts | **5,412** | 5,417 | 1,080 |
| contacts per row | **5.011** | 5.016 | 1.000 |
| repeated speech seconds | **15,456.80** | 15,459.76 | 3,084.53 |
| prompt tokens | **59,777,211** | 45,998,267 | 2,459,915 |
| completion tokens | **251,599** | 255,153 | 26,764 |
| native task-contract tool calls | **1,080** | 1,082 | 0 |
| summed request latency (s) | 65,077.4 | 46,114.7 | 1,185.9 |
| GPU active seconds | **16,995.6** | 12,196.6 | 313.5 |
| **GPU hours** | **4.7210** | 3.3880 | 0.0871 |
| generation wall seconds | 17,250.2 | not in its receipts | 450.6 |
| slot occupancy | 0.943 | not in its receipts | 0.658 |
| mean utilisation (%) | 91.77 | 88.73 | 55.66 |
| parked fraction | 0.014 | 0.022 | 0.281 |
| mean latency (s) | 12.025 | not in its receipts | 1.098 |
| CPU preprocess seconds / workers | 14.20 / 8 | not in its receipts | 13.03 / 8 |
| official scoring seconds / jobs | 339.67 / **1** | not in its receipts | 156.42 / 1 |

GPU hours **+1.3330 (+39.35 %)** against the anchor for **five fewer contacts**. The anchor predates
`flight-receipts.json`, so its wall, occupancy and latency figures are not on file; its GPU seconds
come from its own session-attach monitor summary.

**Prompt fit.** All **5,412** request-fit receipts are present and **every request fits**; 21,648
FIT endpoints, exactly four per contact. Minimum margin **6,690 tokens** in the `planner` phase;
maximum required **17,886** of the 24,576-token slot.

| phase | contacts | endpoints | max required tokens | min margin | registered model-free bound / margin |
| --- | ---: | ---: | ---: | ---: | --- |
| perception | 1,080 | 4,320 | 4,526 | 20,050 | 4,458 / 20,118 |
| solver | 1,084 | 4,336 | 16,004 | 8,572 | 15,427 / 9,149 |
| reviewer | 2,164 | 8,656 | 17,882 | 6,694 | 17,319 / 7,257 |
| planner | 1,084 | 4,336 | **17,886** | **6,690** | 17,327 / 7,249 |

The realized worst case exceeded the preregistration's section-8 word-proxy bound by 559 tokens on
the Planner (17,886 against 17,327) and still fit with 6,690 tokens of margin. The anchor's own
maximum was 15,382 with a 9,194-token margin.

## What is not claimed

- No superiority, generalization, paper-scale or held-out claim. TRAIN Fold A is an exposed
  discovery roster; nothing here is said about Fold B, DEV-1000 or the test split, which stay
  unread.
- **No per-half attribution.** The cell moves the standing fallback candidate and the
  intent-boundaries v2 store together. That the fallback was selected zero times is a fact about the
  *selection*, not a decomposition of the score: the store revision changed the Perception knowledge
  block on 379 of 1,080 first requests, and only cell B4c isolates it.
- No causal claim that the extra slot-card supply caused the slot-level fall. The association is
  reported with its interval and its McNemar p; the covariate is named, not tested.
- The A3 row ceilings (34 and 11) are upper bounds on what a fix can touch, never predicted gains.
- Nothing about whether the revised card *language* is better in general; this measures one frozen
  core on one roster under one retrieval geometry.
- Nothing about the review loop, which is held identical to the anchor.

## The harness-admission consequence (a proposal for the coordinator)

This verdict does not write `docs/receipts/harness-admission.json`; the receipt is the coordinator's
to close and `scripts/checks/harness_admission_check.py` is its oracle. Proposed entry:

- **module**: standing `general_quirky` fallback candidate (A3 FIX-1) together with the
  intent-boundaries store v2 carrying the one-directional qa/general contrast (A3 FIX-2)
- **carrier**: `slurp`
- **class**: `stores`
- **key**: this cell moves **two** `stores`-class keys and therefore cannot claim the switch rule's
  one-key form. They are `knowledge_stores.intent-boundaries` in the **repin** form, and
  `knowledge_stores.slot-contracts` in the option form, whose only moved leaf is
  `candidate_supply.solver.fallback_candidates` (its release and snapshot pins stay at v1 on both
  arms). The mirrored `knowledge_views` leaf
  `phase_material.perception.fill_params.fallback_candidates` moves with it, by design and at its
  own consumption site; the third declaration surface, `native_episode.role_context.params`, is
  unreachable on this base because the anchor declares no `role_context` block. **The coordinator
  may prefer to record two entries rather than one**; cell B4c exists precisely because one entry
  cannot honestly carry both halves.
- **off**: `knowledge_stores.intent-boundaries` at the v1 pins (release
  `2e51c14b4f1c3a122968bc0fd7809523470aad80923ff87c1ce9992ed8d3beb4`, snapshot
  `5520b8449b627530227563d1f8db71f8a391f20f7d0ff7d7bd439e28ec6e48fe`) and
  `candidate_supply.solver` **without** a `fallback_candidates` leaf -- which is what the sealed
  dual-store anchor carries
- **on**: `knowledge_stores.intent-boundaries` at the v2 pins (release
  `31eb595b54088a21e45daf1acfe790d545e8a4d5330acb3ee4e19f6e1607bc95`, snapshot
  `8a27424a84d5b419e033391b9bba00f30952de520c993237ea0219a9978c07c5`) and
  `candidate_supply.solver.fallback_candidates = ["general_quirky"]` with the mirrored
  `phase_material.perception.fill_params.fallback_candidates`, exactly as composed into
  `configs/baseline/slurp-native-anchor-fallback-quirky-intent-v2-train-fold-a-v2.json`; the flown
  bytes are pinned by composed config
  `a07e895cf893bf2a8ba348449e949f3b0db18808d4435a3670ef49fa37f452d2`
- **comparator**: `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1` /
  `attempt-slurp-native-dual-store-train-fold-a-anchor-generation-recovery-v1`, the sealed
  dual-store anchor; never re-flown or re-scored
- **row**: `SAEA-SLURP-NATIVE-FALLBACK-QUIRKY-INTENT-V2-ANCHOR-TRAIN-FOLD-A-V2`
- **status**: **HARMFUL** -- the table's status for an entry where a gating guard fails; it stays in
  the record as a documented negative and never enters a plan
- **status_basis**: intent (the cell's registered primary) 77.9630 -> 78.7037, **+0.7407 pp CI95
  [-0.3031, +1.7544]**, conjunct (a) fails because the lower bound is not above zero; official
  pooled SLU-F1 48.5336 -> 47.8287, **-0.7049 pp CI95 [-2.2930, +0.8861]**, whose lower bound is at
  or below the -1.1218 pp own-null margin, which is the HARMFUL clause that fires. Conjunct (c)
  passes on all three scorings (official +0.7407, projection v3 +0.2778, TRAIN symmetric +0.7407,
  same sign) and conjunct (d) passes (0 of 18 scenarios lose intent beyond the null band, 0
  decision-17 flags). **The failure is one of interval width, not of measured loss**: the SLU point
  estimate is inside its margin and this cell's own SLU CI95 half-width is 1.5895 against the
  borrowed 1.1218. Mechanism as declared but not as hoped: the fallback was appended on 1,052 of
  1,080 rows, raised gold-`general_quirky` candidate coverage from 24.44 % to 100 %, and was
  **selected on zero of those rows**; `general` intent is 36.67 % on both arms and `qa` intent is
  75.00 % on both arms with zero saves and zero harms; the gold `general_quirky` -> `qa_*` confusion
  fell 11 -> 10 while the reverse direction rose 0 -> 1; the realized covariate is +8 median slot
  cards per row, +29.96 % prompt tokens and +39.35 % GPU hours, against pooled span F1 -2.00 and
  per-row exact slot F1 -1.91 (60 harms / 35 saves, p 0.013).
- **evidence**: this verdict; the sealed score
  `633601d1350c4775d63b0ba31fef038370f4615f9ca46b99e58466ad2c34f016`; the run manifest
  `fa93e14923e8192e9426a024792073cf606d9303334d208d68cfd208f02d1036`; the paired read
  `SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-B4A-ANCHOR-V2-PAIRED-ANALYSIS-V1/` with
  `score-contrasts.json`
  `19ce8dc37a0682498b7025610cdc4f01ff586aa5f47a84958efd829a07c064e4` and every other output hashed
  in its `README.md`
- **caveats**: the margins are imported from cell B0r's review-off geometry and are narrower than
  this cell's own measured SLU half-width; the intent, scenario and action means all move positive
  while the three slot-level readings all move negative, and only the slot readings' intervals
  exclude zero; the two FIX-1 rows the arm gets right had `general_quirky` proposed by the core
  itself, not by the fallback; no smoke-to-flight defect and no recovery re-registration occurred.
- **not_admitted_for**: any default plan; and, per owner decision 9 of 2026-09-17, **cell B4c is not
  flown**.

**Owner decision 30.** Cell B4a is an **effectiveness** cell, so this NEUTRAL-or-HARMFUL read
**advances the three-consecutive headroom-exhausted streak**. After the B7a v2 read of 2026-09-19
the streak stood at **one**; with this verdict it stands at **two**. One more consecutive
NEUTRAL/HARMFUL effectiveness read fires the trigger. (Efficiency cells such as EFF-1 do not count.)

## Exposure-ledger closure inputs (the coordinator edits the ledger; this read does not)

| row | registered | actual |
| --- | --- | --- |
| `SAEA-SLURP-NATIVE-FALLBACK-QUIRKY-INTENT-V2-ANCHOR-TRAIN-FOLD-A-V2` | 11,880 calls / 33,930 speech seconds / 12.0 GPU hours / 6,480 task-contract calls | **5,412 calls / 15,456.797250 speech seconds**; 5,412 request-fit receipts, all fitting; **1,080** native task-contract tool calls; **4.7210** GPU hours from the serving monitor; one official complete scoring job; 0 ASR, encoder and paid-API calls |
| `SAEA-SLURP-NATIVE-FALLBACK-QUIRKY-INTENT-V2-ANCHOR-TRAIN-FOLD-A-FIT-V2` | 47,520 endpoints / 33,930 speech seconds | **21,648 endpoints over 5,412 receipts** under `SPEECHRL_DATA_DIR/prepared/SAEA-SLURP-NATIVE-FALLBACK-QUIRKY-INTENT-V2-ANCHOR-TRAIN-FOLD-A-FIT-V2/`; model-free |

Attempt state FINALIZED;
`SPEECHRL_DATA_DIR/attempts/SAEA-SLURP-NATIVE-FALLBACK-QUIRKY-INTENT-V2-ANCHOR-TRAIN-FOLD-A-V2/`
holds exactly one attempt file, reserving 11,880 calls / 33,930 seconds and recording 5,412 /
15,456.797250 actual. Run-cumulative headroom after this flight: 6,468 calls and 18,473.20 speech
seconds.

## Artefacts

Analysis root `SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-B4A-ANCHOR-V2-PAIRED-ANALYSIS-V1/`, the path
the recipe's `output.analysis_root` names.

| file | SHA-256 |
| --- | --- |
| `score-contrasts.json` | `19ce8dc37a0682498b7025610cdc4f01ff586aa5f47a84958efd829a07c064e4` |
| `README.md` | `1bc8ad98c8de7afc3a69b73a486e58d23dae67fc9ff9b4d3a3d6bf37894c0265` |
| `per-scenario-tables.json` | `f0dc749d4de041544d2b940139859183b385266079a3a5bd5c7cace431c5c22b` |
| `flight-diagnostics.json` | `1b740d1e8e5869b2eae7ec0d4f22bfeb5fd6ea95e491a91dfecd70ebbd77c484` |
| `b4a_paired_read.py` (the driver, copied into the package) | `d3b5bb4caf7e911270cdf0d059960b4be4ef3e995586a662bb3a889e88a40f67` |

Every input and output of the read -- the three arms' sealed scores, manifests and outputs, both
phase artefacts, both traces, the arm's flight receipts, the three generation manifests, the sealed
A3 join, the roster, the roster metadata, the umbrella dataset lock, the nine authority documents
and the twelve estimator implementations -- is hashed in `score-contrasts.json` under `inputs` and
`outputs`, and the projection-v3 and symmetric score files and the outputs copies are hashed there
too.

**One registered path differs between the recipe and the task brief, and the recipe wins:** the
analysis root is `SAEA-SLURP-B4A-ANCHOR-V2-PAIRED-ANALYSIS-V1`, not
`SAEA-SLURP-B4A-FALLBACK-QUIRKY-ANCHOR-V2-PAIRED-ANALYSIS-V1`. The verdict path is the brief's and
the exposure ledger's, `docs/results/2026-09-19-slurp-b4a-fallback-quirky-anchor-v2-verdict.md`,
rather than the recipe's stale `2026-09-17-slurp-b4a-anchor-v2-verdict.md`, because the ledger row
already names this path. The brief's extra deliverable `per-scenario-tables.json` was written as
well, beside the recipe's two named files.

The driver is an adapted copy of two sealed precedent drivers whose estimator calls are reproduced
byte for byte -- `analysis/SAEA-SLURP-B7A-NCP-L1-ANCHOR-V2-PAIRED-ANALYSIS-V1/b7a2_paired_read.py`
and `analysis/SAEA-SLURP-B4B-REPLICATE-PAIRED-ANALYSIS-V1/b4b_replicate_paired_read.py`. Only the
arm list, the contrast list, the decision block and this cell's own fallback / coverage / confusion
diagnostics are new; every seed, draw count and interval level is the precedents'.
`analysis.score_compare_cli` is deliberately not the runner, because it hard-codes CI90 and DEV
population names.

## Exposure

**Zero model, tokenizer, encoder, ASR and server contacts.** Execution profile `model-free-check`.
The only scorer invocations are the model-free projection-v3 and TRAIN symmetric scorings, three
arms each, every one over a COPY of that arm's sealed `outputs.jsonl` written under the analysis
root. No sealed file was opened for writing, moved or renamed; nothing was written under
`SPEECHRL_DATA_DIR/runs` or `SPEECHRL_DATA_DIR/attempts`; no serving session, flight worktree,
scheduled task or flight lock was touched; no exposure-ledger row, harness-admission receipt,
results ledger or readiness document was edited. Gold intent ids were read to COUNT coverage and
confusion and are never written out per row: this read reports counts, aggregate numbers, scenario
names, sample ids and content hashes only, and no utterance text, transcript, gold filler or model
output was printed or persisted.
