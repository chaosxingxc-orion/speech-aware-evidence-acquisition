# NEUTRAL -- cell B8b-anchor (the Reviewer slot-audit context block) on the sealed dual-store anchor, SLURP TRAIN A

Status: **NEUTRAL**, the word the registered decision rule names. Against the sealed dual-store
anchor on the same 1,080 TRAIN Fold A rows the official pooled SLU micro F1 delta is **+0.8698 pp,
CI95 [-0.6341, +2.3654]** and the intent (joint scenario+action) guard is **+1.2037 pp, CI95
[-0.1852, +2.5926]**. Conjunct (a) of the ADMITTED rule fails -- the CI95 lower bound of the primary
is not above zero -- so the cell is not admitted. HARMFUL, which the rule reads **first**, does not
apply: there is no measured loss on either axis, both point estimates are **positive**, and neither
CI95 upper bound is below zero.

**Every reading moves the same way, and every reading is positive.** Official pooled SLU-F1
**+0.8698**, projection v3 **+1.1276**, TRAIN symmetric **+1.0559**; intent **+1.2037**, scenario
**+0.7407**, action **+1.3889**, official span F1 **+0.5565**, per-row mean official SLU-F1
**+1.0105**, per-row exact slot F1 **+0.5147**. Not one of the eighteen scenarios loses intent
beyond the null band and not one is flagged under owner decision 17. Under owner decision 25 this is
**recorded as a beneficial but not CI95-proven movement** and is never claimed as an admission. What
stops the admission is interval width: the primary's own CI95 half-width is **1.4998 pp**, 33.7 %
wider than the B0r own-null half-width the margins come from, so a +0.87 pp gain cannot clear zero.

Root: the B8b-anchor paired-read agent, 2026-09-20. Read **once**, from the single official score of
the complete 1,080-row manifest; no row was filtered, no repeat-to-pass was taken, and no comparator
was re-flown or re-scored. Recipe:
`docs/readiness/2026-09-19-slurp-b8b-anchor-reviewer-audit-v1-resume-v1/analysis-recipe-v1.json`
(recipe id `slurp-b8b-anchor-reviewer-audit-resume-v1`). Preregistration:
`docs/readiness/2026-09-19-slurp-b8b-anchor-reviewer-audit-v1-preregistration.md`, whose question,
arms, metrics, resampling, margins and decision rule the resume addendum
(`…-resume-v1.md`) leaves unchanged. Analysis root:
`SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1`.

## What flew, and the resume custody that had to close first

Run `SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1`, attempt
`attempt-slurp-native-reviewer-audit-anchor-train-fold-a-generation-v1-resume`, **FINALIZED**,
manifest **COMPLETED** at study commit `2f185b134badd34fe6ad841fcfb9e477032bcec2` with
`study_repo_dirt` **empty**, composed config
`1170659f0fcda16ee5f051b5be85fda869e2e986dc150a478dfc26bbcafe2ead` and protocol
`ffb4595b210aa3db754bb356f9573e9efc3830ab85c80d39ad4dea438ac325db` -- the two values the resume
package registered pre-flip -- arm `speech-feature-query-native-tools`, profile
`bounded-discovery-probe`, split identity
`61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, role `discovery`, 1,080 ordered
ids. Sealed bytes, each re-hashed by this read before it was opened:

| artefact | SHA-256 |
| --- | --- |
| run manifest | `88a03cd570eaf7aa75986e7e7a0f501c15fe972e895cd3c4565154dd98ba0d7a` |
| official score | `78e70f779a6075f77c9c638b67a264670bf87dbaaafbb9765162a84cbd4a8b1a` |
| outputs | `fba9936bca5876ab187bdd776eb74660fd71236ccd9ee764cdfe419cf96081fa` |

One official complete scoring job through `core.scoring_batch` (`slurp-slu-official-train`,
evaluator commit `8eb16545762be97ace75334109d73824217311f1`, identity check passed, no label
projection), never sharded, the number this verdict reads.

This is an **E10 mode-A resume-recovery seal** (owner decision 22): the arm aborted on 2026-09-19 at
2,016 contacts when the Reviewer's ReAct loop exhausted three iterations without an answer and the
runtime had no disposition for it. The resume kept the predecessor's complete rows and re-flew the
rest. `resume-custody.json` closes the reading rule before any number was read:

| custody fact | declared | re-proved here |
| --- | --- | --- |
| predecessor trace SHA-256 | `d495661d…a6d84e3` | same, re-hashed on disk |
| trace records / contacts | 13,282 / 2,016 | 13,282 / 2,016 |
| rows COMPLETE (kept) | 378 | 378, equal to the predecessor's complete set |
| rows INCOMPLETE (re-flown in full) | 2 | 2, the two exhausted visits' rows |
| rows never started (flown) | 700 | 700; flown total 702 |
| sorted kept-id SHA-256 | `19b8b9e0…a91cfaccf` | same, recomputed |
| kept rows also flown by the resume | 0 | 0 |
| kept + flown covers the roster | yes | yes, exactly 1,080 |

**I7r holds byte for byte.** All **378** kept rows deliver text whose SHA-256 equals the
predecessor's recorded delivery *and* the sealed `response_text_sha256`; all **378** carry an episode
receipt byte-identical to the one replayed from the predecessor trace; and
`core.bundle.verify_bundle` on the sealed manifest **PASSES**, which includes
`_verify_resume_custody` (invariant I7r). The two partial rows,
`slurp:train:004389:audio-1502113264` and `slurp:train:004534:audio-1498647066-headset`, were
re-flown in full and **neither exhausted again**: they spent 9 and 5 contacts, carry no
`react_exhaustion` record and no terminal disposition, and delivered normally.

Per the recipe's own reading rule, **no metric below is split by kept versus flown**: *"No
stratification, contrast or diagnostic of this recipe may be conditioned on whether a row was kept or
flown."* The spawn brief asked for that split; the recipe wins and it was not taken. The counts, the
kept-id hash and the custody proof above are what the recipe does require.

**Both arms are NODE-FREE.** Cell B8b-anchor and the sealed dual-store anchor were both registered
before module M3, the delivery normaliser, entered the default plan, so neither carries it. The
number is therefore not directly comparable to a later default-plan number that does.

## The STOP condition, closed before any B8b table was read

The registered comparator aggregates reproduce from the sealed bytes, and
`analysis.null_calibration.pooled_f1` reproduces each arm's own official pooled aggregate to 1e-6:

| check | registered | recomputed |
| --- | ---: | ---: |
| anchor official SLU F1 | 48.53 | 48.5336 |
| anchor official intent | 77.96 | 77.9630 |
| anchor official scenario | 84.81 | 84.8148 |
| anchor official action | 79.26 | 79.2593 |
| anchor official span F1 | 29.50 | 29.4985 |
| anchor projection v3 (all five) | 51.99 / 79.35 / 85.46 / 80.65 / 40.30 | 51.9946 / 79.3519 / 85.4630 / 80.6481 / 40.3025 |

## (a) Cell B8b-anchor minus the sealed dual-store anchor -- the PRIMARY contrast (percentage points)

delta = B8b-anchor minus the anchor; negative is worse. **Registered estimator: paired per-row
bootstrap, 10,000 draws, seed 20260919, CI95** (the recipe's `resampling` block). The two intervals
to its right were computed in the same pass and are **not registered by this recipe**; they are
carried for continuity with the precedent cells, decide nothing, and change nothing.

| metric | estimand | anchor | B8b-anchor | delta | **registered CI95** | registered CI90 | CI95 half-width | speaker-cluster CI95 (unreg.) | scenario-strat. CI95 (unreg.) | equal-scenario delta |
| --- | --- | ---: | ---: | ---: | --- | --- | ---: | --- | --- | ---: |
| **Official pooled SLU micro F1** | pooled count F1 | 48.53 | 49.40 | **+0.87** | **[-0.63, +2.37]** | [-0.40, +2.13] | 1.4998 | [-0.45, +2.17] | [-0.62, +2.37] | +0.78 |
| **Intent (joint scenario+action)** | mean per row | 77.96 | 79.17 | **+1.20** | **[-0.19, +2.59]** | [+0.00, +2.31] | 1.3889 | [-0.20, +2.52] | [-0.19, +2.59] | +1.20 |
| Scenario accuracy | mean per row | 84.81 | 85.56 | +0.74 | [-0.46, +2.04] | [-0.28, +1.76] | 1.2500 | [-0.49, +1.84] | [-0.46, +1.94] | +0.74 |
| Action accuracy | mean per row | 79.26 | 80.65 | **+1.39** | **[+0.09, +2.69]** | [+0.28, +2.50] | 1.2963 | [+0.00, +2.72] | [+0.00, +2.78] | +1.39 |
| Official span F1 (pooled) | pooled count F1 | 29.50 | 30.05 | +0.56 | [-1.22, +2.38] | [-0.96, +2.09] | 1.7995 | [-0.92, +2.15] | [-1.24, +2.32] | +0.31 |
| Official SLU F1 (per-row mean) | mean per row | 30.29 | 31.30 | +1.01 | [-0.13, +2.16] | [+0.05, +1.96] | 1.1456 | [-0.01, +2.04] | [-0.10, +2.18] | +1.01 |
| Exact slot F1 (per-row mean) | mean per row | 19.02 | 19.54 | +0.51 | [-0.63, +1.67] | [-0.45, +1.47] | 1.1494 | [-0.48, +1.55] | [-0.60, +1.67] | +0.51 |

Saves, harms and ties, with the exact two-sided McNemar p:

| per-row metric | saves | harms | ties | exact two-sided McNemar p |
| --- | ---: | ---: | ---: | --- |
| scenario_action_exact (intent) | 35 | 22 | 1023 | 1.112e-01 |
| scenario_exact | 27 | 19 | 1034 | 3.020e-01 |
| action_exact | 35 | 20 | 1025 | 5.806e-02 |
| slot_f1_exact_f1 | 39 | 36 | 1005 | 8.176e-01 |
| slu_f1_f1 | 84 | 74 | 922 | 4.741e-01 |

**Every metric moves the same way, pooled and per-row alike.** That is the opposite of cell B7a v2,
where the pooled count F1 and the per-row means disagreed in sign. Here the pooled primary, both
per-row means and all three accuracies point up together, and saves exceed harms on every one of the
five per-row metrics.

The arm reaches official pooled SLU-F1 **49.4034** and intent **79.1667**. As a **fact**: 49.40 does
**not** clear the 64.00 development bar. This is not a bar attempt, and nothing here is claimed as
"replicated on the same roster". Under owner decision 28 all three numbers are **development**
numbers on an exposed discovery roster and are never compared with a published TEST baseline.

## The decision rule, applied exactly as registered

**HARMFUL is read first** (owner decision 25, Method B). It requires a *measured* loss: a point
estimate of the official pooled SLU-F1 delta or of the intent delta below **-h** (-1.1218 /
-1.0051), or a CI95 **upper** bound below zero. The point estimates are **+0.8698** and **+1.2037**,
both positive; the CI95 upper bounds are **+2.3654** and **+2.5926**. **Not HARMFUL.**

ADMITTED requires all four:

| conjunct | requirement | reading | holds |
| --- | --- | --- | --- |
| 1 | CI95 **lower** bound of the paired official pooled SLU-F1 delta **> 0** | **-0.6341** | **NO** |
| 2 | intent non-inferior: CI95 lower bound **> -1.0051** | **-0.1852** | yes |
| 3 | TRAIN symmetric `slurp-slu-f1-normalized-v1-train` **agrees in sign** with the unprojected primary | symmetric **+1.0559**, official **+0.8698**, both positive | yes |
| 4 | **no scenario** loses intent beyond the null band (no scenario's paired intent CI95 upper bound below zero) | 0 of 18 | yes |

Conjunct 1 fails, so the read is **NEUTRAL**. Stating the rule's own clause in its own words: the
primary interval **straddles zero**, so **"non-inferiority not proven"** is the phrase the rule
attaches to that straddle, and no proven gain may be claimed from it. What the interval *does*
establish, and what this verdict does claim, is that **both** the primary and the guard clear the
registered own-null margins on the loss side by a wide distance (-0.6341 against -1.1218; -0.1852
against -1.0051) and that every point estimate is positive. Under owner decision 25 the movement is
**recorded as beneficial but not CI95-proven**.

Margins: cell B0r's own null on this exact TRAIN A roster and geometry, **h_SLU = 1.1218**,
**h_intent = 1.0051** (owner decision 38; the sealed anchor has no request-identical replicate of
its own, so B0r's own null is the registered fallback and the retired imported DEV-1000 half-widths
are never used).

## (b) The two companion scorings -- diagnostics only (owner decisions 7, 14, 23)

Each was run **once** over a COPY of each arm's sealed outputs, under `v3/` and `symmetric/`; the
anchor's registered v3 aggregates reproduce to the hundredth.

| scoring | anchor | B8b-anchor | delta | registered CI95 | agrees in sign with the official primary |
| --- | ---: | ---: | ---: | --- | --- |
| official pooled SLU-F1 (decides) | 48.5336 | 49.4034 | **+0.8698** | [-0.6341, +2.3654] | -- |
| projection v3 pooled SLU-F1 | 51.9946 | 53.1222 | +1.1276 | [-0.6024, +2.8197] | yes |
| TRAIN symmetric pooled SLU-F1 | 52.0887 | 53.1446 | +1.0559 | [-0.6790, +2.7748] | yes (conjunct 3) |
| projection v3 intent | 79.3519 | 80.2778 | +0.9259 | [-0.3704, +2.2222] | yes |
| projection v3 pooled span F1 | 40.3025 | 41.4054 | +1.1029 | [-0.7311, +2.9438] | yes |
| TRAIN symmetric pooled span F1 | 41.3830 | 42.2703 | +0.8872 | [-0.9946, +2.7827] | yes |

The symmetric normaliser is `saea-slurp-slot-normalizer-v1` with **34** false merges on both arms --
identical, so the symmetric reading is not an artefact of asymmetric normalisation.

## Per-scenario intent -- the registered conjunct 4, and owner decision 17

Paired per-row bootstrap within each scenario, same draws and seed. 60 rows per scenario, 18
scenarios, natural mixture and equal-stratum weightings both reported above.

| scenario | n | anchor | B8b-anchor | delta | CI95 | saves | harms | net harmed |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| cooking | 60 | 85.00 | 81.67 | -3.33 | [-10.00, +3.33] | 1 | 3 | +2 |
| general | 60 | 36.67 | 33.33 | -3.33 | [-13.33, +5.00] | 3 | 5 | +2 |
| transport | 60 | 86.67 | 85.00 | -1.67 | [-5.00, **+0.00**] | 0 | 1 | +1 |
| iot | 60 | 86.67 | 86.67 | +0.00 | [+0.00, +0.00] | 0 | 0 | 0 |
| lists | 60 | 83.33 | 83.33 | +0.00 | [+0.00, +0.00] | 0 | 0 | 0 |
| news | 60 | 80.00 | 80.00 | +0.00 | [-5.00, +5.00] | 1 | 1 | 0 |
| qa | 60 | 75.00 | 75.00 | +0.00 | [+0.00, +0.00] | 0 | 0 | 0 |
| recommendation | 60 | 90.00 | 90.00 | +0.00 | [-5.00, +5.00] | 1 | 1 | 0 |
| takeaway | 60 | 85.00 | 85.00 | +0.00 | [-6.67, +6.67] | 2 | 2 | 0 |
| weather | 60 | 90.00 | 90.00 | +0.00 | [+0.00, +0.00] | 0 | 0 | 0 |
| music | 60 | 76.67 | 78.33 | +1.67 | [-5.00, +10.00] | 3 | 2 | -1 |
| calendar | 60 | 75.00 | 76.67 | +1.67 | [-3.33, +8.33] | 2 | 1 | -1 |
| email | 60 | 85.00 | 86.67 | +1.67 | [+0.00, +5.00] | 1 | 0 | -1 |
| social | 60 | 66.67 | 68.33 | +1.67 | [+0.00, +5.00] | 1 | 0 | -1 |
| datetime | 60 | 83.33 | 88.33 | +5.00 | [+0.00, +11.67] | 3 | 0 | -3 |
| play | 60 | 58.33 | 63.33 | +5.00 | [-6.67, +16.67] | 8 | 5 | -3 |
| alarm | 60 | 83.33 | 90.00 | +6.67 | [+0.00, +15.00] | 5 | 1 | -4 |
| audio | 60 | 76.67 | 83.33 | +6.67 | [+1.67, +13.33] | 4 | 0 | -4 |

**Conjunct 4 holds: no scenario's intent CI95 upper bound lies below zero.** Transport is the closest
case -- its upper bound is exactly **+0.00**, on a single harmed row -- and is recorded as such
rather than rounded away. **No scenario reaches the owner decision-17 flag** (five or more net harmed
rows); the worst is cooking and general at two each. Fourteen scenarios tie or gain; four lose; the
whole loss side is six harmed rows across three scenarios.

## What the block actually did -- the cell's own target

The audit block attaches to the Reviewer's `current-draft` boundary (`B-DRAFT-REV`). Over the sealed
1,080-row manifest:

| slot-audit fact | count |
| --- | ---: |
| Reviewer draft-boundary receipts carrying a `slot_audit` row | 2,564 |
| `applied: true` (the block was rendered) | **2,554** |
| `applied: false` | **10**, every one with machine reason **`draft-unparsed`** -- the only reason this attachment can emit |
| rows with at least one `slot_audit` receipt | 1,080 of 1,080 |
| rows with at least one **applied** block | 1,076 |
| contacts whose drafted intent is in the construction table | 2,512 (52 not) |
| block size, characters | median 523, mean 542, p90 718, min 372, max 1,068 |

**The block-rendered receipt.** All **2,554** applied contacts have a boundary `rendered_sha256`
that differs from their source's `content_sha256`, and **zero** applied contacts render their
source's bytes. Across the whole flight this is the **only** place where a `level: "raw"` row's
rendered bytes are not its source's -- exactly the registered mechanism, and the
`raw_reason` distribution below shows it nowhere else.

**The four flags, over every Reviewer contact including the zeros:**

| flag | contacts where it fired | rows where it fired |
| --- | ---: | ---: |
| MISSING-COMMON | 669 | 272 |
| EMPTY-DRAFT | 459 | 204 |
| TYPE-UNSEEN | 126 | 48 |
| REPRESENTATION | 46 | 23 |
| **at least one flag** | **997** | **419** |

**Flagged versus unflagged rows -- a DIAGNOSTIC, never an attribution.** The four flags move
together and no single flag is separately admitted; a flagged-row delta is a description of where the
movement sits, not a causal claim.

| population | rows | intent delta | per-row official SLU-F1 delta | rows with an executed revision |
| --- | ---: | ---: | ---: | ---: |
| at least one flag fired | 419 | **+2.63** | **+1.82** | 76 |
| no flag fired | 661 | +0.30 | +0.50 | 28 |
| EMPTY-DRAFT | 204 | +1.47 | +2.13 | 38 |
| MISSING-COMMON | 272 | +0.74 | +2.15 | 56 |
| TYPE-UNSEEN | 48 | +0.00 | +0.26 | 17 |
| REPRESENTATION | 23 | +17.39 | +4.05 | 0 |

Nearly the whole movement sits on the 419 rows where a flag fired. The REPRESENTATION column is 23
rows and is reported only because the recipe demands every flag; it carries no weight and no claim.

**The Reviewer criticises far more, and the loop executes it.** Planner routes, delivered manifest:

| | anchor | B8b-anchor |
| --- | ---: | ---: |
| route decisions | 1,085 | 1,178 |
| ACCEPT | 1,079 | 1,071 |
| REVISE | **6** | **107** |
| rows with at least one REVISE | 5 | 104 |
| executed revisions | **5** | **101** |
| `revision_limit` terminal dispositions | 1 | 3 |

That is the mechanism working as designed: an audit block the Reviewer can criticise against turns
6 REVISE tokens into 107, and 101 of them execute. It is also where the extra cost comes from.

## The per-boundary node-context aggregate

Under the composed bare-`raw` arm of `native_episode.context_policy` the policy id is
`raw-node-context-v1` and **every** boundary row is `level: "raw"` with `parse_status: "not-parsed"`.
Rows whose rendered bytes equal their source's content: **every row except the 2,554 applied
Reviewer draft rows**, exactly as the preregistration requires.

| boundary | consumer | class | rows | rendered = source | rendered differs | raw_reason distribution |
| --- | --- | --- | ---: | ---: | ---: | --- |
| B-DRAFT-REV | reviewer | current-draft | 2,564 | 10 | **2,554** | none |
| B-CAND-REV | reviewer | candidate-hypothesis | 2,362 | 2,362 | 0 | none |
| B-TOOL-REVIEWER | reviewer | tool-observation | 1,381 | 1,381 | 0 | live-tool-chain 1,179; none 202 |
| B-UNDECLARED | reviewer | review-finding | 3,064 | 3,064 | 0 | boundary-not-declared 1,683; native-tool-call-source 1,381 |
| B-CAND-SOL | solver | candidate-hypothesis | 1,184 | 1,184 | 0 | none |
| B-DRAFT-SOL | solver | current-draft | 104 | 104 | 0 | none |
| B-PLAN-SOL | solver | plan-action | 104 | 104 | 0 | none |
| B-REVIEW-SOL | solver | review-finding | 208 | 208 | 0 | native-tool-call-source 104; none 104 |
| B-TOOL-SOLVER | solver | tool-observation | 104 | 104 | 0 | none |
| B-DRAFT-PLAN | planner | current-draft | 1,279 | 1,279 | 0 | none |
| B-REVIEW-PLAN | planner | review-finding | 2,552 | 2,552 | 0 | native-tool-call-source 1,274; none 1,278 |
| B-TOOL-PLANNER | planner | tool-observation | 1,274 | 1,274 | 0 | none |

**The sealed anchor emits no such receipts at all** -- it was flown before the node-context receipt
existed -- so the aggregate has no comparator column. That is a fact about the comparator's age, not
about this cell.

## Failure-mode dispositions, both of them measured rather than assumed

| disposition | anchor | B8b-anchor |
| --- | ---: | ---: |
| `terminal_disposition.reason == "finite_completion"` (item E13) | **0** | **6** |
| `react_exhaustion` rows (item E22) | **0** | **1** |
| `react_exhaustion` visits | 0 | **1**, with `identical_calls: true` |
| `planner_action_illegal` | 0 | **0** |
| `context_compaction` rows / contacts | -- | 0 / 0 |

**The six finite-completion rows** are all the Reviewer at `finish_reason: "length"`, all delivered
the latest Solver draft (none abstained), at revision counts 0 or 1:
`slurp:train:001479:audio-1488969263`, `…:001642:audio--1504198588`, `…:002147:audio-1434541391`,
`…:004725:audio-1499697354`, `…:015278:audio-1497438167-headset`, `…:015692:audio-1497268806`. Three
were retained by the predecessor attempt and are among the 378 kept rows; three by the resume. Every
one is retained and scored as delivered and none was filtered. The anchor flew **without** the key
and its exposure receipt records **zero** finite completions, so the asymmetry is **measured, not
assumed**, and nothing here claims a retained finite-completion row is as good as an uninterrupted
one.

**The single ReAct exhaustion** is on `slurp:train:012386:audio-1490371959`, role visit index 5,
stage `review`, revision count 1: the Reviewer used all three iterations calling
`saea-tool-task-contract-v1`, with **identical arguments each time** (`identical_calls: true`,
arguments digest `44136fa3…` = the empty object). Under the armed
`react_exhaustion_policy = "continue-without-answer"` the visit ended with an empty finding, the
Planner routed normally, **no contact was retried or added**, and the row delivered. That single
disposition is what cost the aborted attempt 2,016 contacts a day earlier. The campaign logs agree
with the receipts: the aborted attempt reached `ReAct iteration 3/3` on **2** of 410 Reviewer visits;
the resume on **1** of 778; cell B1r's comparator log on **0** of 1,092.

ReAct iteration depth over the delivered manifest, from the sealed receipts:

| Reviewer visits reaching | anchor | B8b-anchor |
| --- | ---: | ---: |
| 1 contact | 3 | 7 |
| 2 contacts | 1,082 | 1,176 |
| 3 contacts | **0** | **1** |
| total visits | 1,085 | 1,184 |

## Reviewer parse rate, delivery shape and tool calls

**Reviewer parse rate under the repository's registered findings parser**
(`rails.review_findings.parse_review_findings`): **0 parsed of 2,362** on the arm and **0 of 2,167**
on the anchor -- 100 % unparsed on both sides. This cell declares no producer response format, so the
rate **gates nothing**; it is reported for continuity with the retired Node Context Policy L1
diagnostics, whose own finding was the same.

**Delivery shape.** Zero rows on either arm deliver a tool-call-shaped answer: no `<tool_call>` tag,
no delivery naming the task-contract tool, no JSON object with `name`/`arguments`, no empty delivery.
Delivered length median 93 characters (anchor 94). The official scorer could not parse **5** arm rows
and **7** anchor rows; all twelve are retained and scored as delivered.

**Native task-contract tool calls.** The arm's delivered manifest spends about one call per Reviewer
visit, the registered expectation: 774 on the resume attempt plus 413 on the predecessor against
1,184 Reviewer visits, versus the anchor's 1,082 against 1,085 visits. Only
`saea-tool-task-contract-v1` is ever called, on the Reviewer phase only, on both arms. The declared
ceiling of 6,480 is not approached.

## Wire identity -- what this read could and could not confirm

The preregistration (section 3) claims that under the composed bare-raw policy the only place a byte
moves is the Reviewer's draft boundary, and that *"Perception, Solver and Planner requests are
byte-identical to the anchor's"*. Compared per row on the first contact of each role, by the sealed
EFF-1 driver's model-facing request digest (request id, evidence-provenance relpaths and the
scheduler's `id_slot` excluded as bookkeeping):

| role | first contact byte-identical to the anchor's | differs | identical once provenance and history are also excluded |
| --- | ---: | ---: | ---: |
| perception | **1,080 of 1,080** | 0 | 1,080 |
| solver | 0 | 1,080 | 774 |
| reviewer | 0 | 1,080 | 774 |
| planner | 0 | 1,077 (3 rows have the role on one arm only) | 772 |

**The Perception half of the claim is proved at the wire**, on every row, which is the model-free
evidence that neither declared key moves a knowledge-selection byte -- and it agrees with the
prepared supply artifact the resume actually flew,
`prepared/SAEA-…-TRAIN-FOLD-A-V1/phase-supply-v2.json` (file SHA-256 `6fdbb074…`, `identity_ok` at
preflight), whose **output** SHA-256 is
`ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` -- the very value the sealed
anchor's own Perception output carries. The re-pin rebuilt the artifact because the composed
configuration differs; it did not move a knowledge byte.
**The Solver and Planner half is NOT reproducible from the sealed traces** and is recorded here as
such. Part of the difference is unavoidable bookkeeping -- this cell carries its own prepared-supply
artifact, whose hash rides every downstream request's evidence provenance -- and with provenance and
conversation history excluded the first Solver, Reviewer and Planner requests still match on 774 of
1,080 rows. The residual 306 rows cannot be attributed without printing request bytes, which this
read must not do; the standing explanation on this machine is that greedy decoding at temperature 0
is not bitwise reproducible across batch compositions, so a differing Perception response changes
what is supplied downstream. **No claim of downstream byte identity is made by this verdict.**

## Cost and efficiency

Per-role prompt tokens over the delivered 1,080-row manifest, beside the anchor's. The block adds
tokens to the **Reviewer** contacts only; the whole-run figure is stated only beside the per-role
one.

| role | contacts (anchor) | contacts (arm) | prompt median (anchor) | prompt median (arm) | delta | prompt total (anchor) | prompt total (arm) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| perception | 1,080 | 1,080 | 3,593.0 | 3,593.0 | **+0.0** | 3,884,813 | **3,884,813** |
| solver | 1,085 | 1,184 | 8,964 | 9,151.0 | +187.0 | 9,492,410 | 10,620,752 |
| reviewer | 2,167 | 2,362 | 9,905 | 10,362.5 | **+457.5 (+4.62 %)** | 21,112,471 | 24,205,504 |
| planner | 1,085 | 1,178 | 10,804 | 11,042.5 | +238.5 | 11,508,573 | 12,787,257 |
| **whole manifest** | **5,417** | **5,804** | -- | -- | -- | **45,998,267** | **51,498,326 (+11.96 %)** |

The **Reviewer per-contact median rises by 457.5 tokens, +4.62 %** -- that is the block's own price,
and it matches its 523-character median. Perception is identical to the token. Everything else above
the Reviewer line is the *loop* getting longer, not the block getting bigger: 101 executed revisions
against 5.

| cost | anchor | B8b-anchor |
| --- | ---: | ---: |
| contacts on the delivered manifest | 5,417 (5.016 per row) | **5,804 (5.374 per row, +7.14 %)** |
| contacts actually spent on the run (both attempts) | -- | **5,822** (2,016 aborted + 3,806 resume) |
| completion tokens, delivered manifest | 255,153 | 306,975 |
| repeated speech seconds, run-cumulative | 15,459.76 | **16,591.81** (5,481.65 + 11,110.17) |
| native task-contract tool calls | 1,082 | 1,187 across both attempts |
| GPU hours | 3.3880 | **3.8464 run-cumulative** = 2.6253 (resume) + 1.2211 (aborted), **+13.53 %** |
| wall clock | not receipted | 9,658.8 s (resume) |
| slot occupancy | not receipted | 0.9310 |
| GPU utilisation / parked | 88.73 % / 0.0219 | **90.82 % / 0.0210** |
| contacts per minute | -- | 23.66 over the attach window; 24.18 over the observed release span |

The resume's own GPU window is the sealed `session-attach-receipt` monitor summary (active 9,451.04 s
of 9,653.74 s wall). The **aborted** attempt sealed no flight receipt and no monitor summary, so its
window was reconstructed from the resident session's `monitor.jsonl` under the summary's own parked
definition; the same code reproduces the resume's sealed summary **exactly**, which is why the
1.2211 GPU-hour figure for the aborted part is stated rather than omitted
(`monitor-windows.json`). The split is therefore **2.6253 sealed + 1.2211 reconstructed**.

**The resume is what made this read affordable.** 2,016 of the run's 5,822 contacts never had to be
paid again; the 378 kept rows carry 1,998 of those contacts into the delivered manifest and only 18
contacts (the two discarded partial rows' predecessor work) were wasted.

**Request fit.** 5,822 request-fit receipts across the two fit attempts (2,016 + 3,806), **every
single one fitting**: minimum margin 7,449 tokens of the 24,576-token live slot, maximum required
17,127. Zero truncations in the server log over the whole flight window, where the join is exact --
**3,806 of 3,806** generation contacts appear as slot release records in the resident session's last
log segment.

**Ledger closure inputs** (the coordinator edits the ledger; this read does not):

| quantity | value | registered ceiling | headroom |
| --- | ---: | ---: | ---: |
| generation contacts, run-cumulative | 5,822 | 11,880 | 6,058 |
| repeated speech seconds, run-cumulative | 16,591.81 | 33,930 | 17,338.19 |
| fit receipts / endpoints | 5,822 receipts (4 endpoints each = 23,288) | 47,520 | 24,232 |
| GPU hours, fit-inclusive | 3.8464 | 12.0 | 8.1536 |
| native task-contract calls | 1,187 | 6,480 | 5,293 |
| official complete scoring jobs | 1 | 1 | 0 |
| ASR / encoder / paid-API calls | 0 | 0 | 0 |

## Harness-admission consequence

Proposed entry for `docs/receipts/harness-admission.json` -- **the coordinator writes the receipt**;
this verdict only proposes it.

| field | value |
| --- | --- |
| class | `episode` |
| key | `native_episode.reviewer_audit` |
| OFF | the key's absence (the sealed anchor's own configuration) |
| ON | `slot-audit-v1`, the released construction view with its two pins and the three registered thresholds (`empty_draft_min_entity_row_share` 0.5, `missing_common_min_row_share` 0.5, `profile_min_row_share` 0.05) |
| status | **NEUTRAL** -- "no harm and no gain; may enter the default plan" |
| row | `SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1` |
| carrier | `slurp` |
| comparator | the sealed dual-store anchor `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1`; never re-flown or re-scored; both arms node-free; the anchor flew without both failure-mode keys (zero finite completions, zero ReAct exhaustions proven), the arm with both (6 and 1 retained) |
| status_basis | official pooled SLU-F1 48.5336 -> 49.4034, **+0.8698 pp CI95 [-0.6341, +2.3654]**; intent 77.9630 -> 79.1667, **+1.2037 pp CI95 [-0.1852, +2.5926]** (1,080 paired TRAIN A rows, paired per-row bootstrap, 10,000 draws, seed 20260919). Conjunct 1 fails on interval width; conjuncts 2, 3 and 4 hold; no measured loss on either axis. Projection v3 +1.1276 and TRAIN symmetric +1.0559 agree in sign. 0 of 18 scenarios breach the band, 0 decision-17 flags, 14 of 18 tie or gain. Cost: 5.374 contacts per row (anchor 5.016), 3.8464 GPU hours run-cumulative (anchor 3.3880, +13.53 %), Reviewer prompt-token median +457.5 (+4.62 %), 101 executed revisions against the anchor's 5. |
| evidence | arm run/attempt above at study commit `2f185b13`; verdict `docs/results/2026-09-19-slurp-b8b-anchor-reviewer-audit-verdict.md`; analysis dir `SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1`; resume custody `resume-custody.json` (I7r, `verify_bundle` PASSED) |
| twin | none flown, and none is owed: the registered twin rule fires only on a **positive CI95 lower bound** against the anchor, which this cell does not have |

## Owner decision 30 -- what this verdict does to the streak

Cell B8b-anchor is an **effectiveness** cell and it reads NEUTRAL, so under owner decision 30 it
**advances the headroom-exhausted streak to three**: cell B7a v2 (HARMFUL, 2026-09-19), cell B4a v2
(HARMFUL, 2026-09-19), cell B8b-anchor (NEUTRAL, this verdict). **Trigger (b) of decision 30 fires:
"three consecutive one-factor cells read NEUTRAL or HARMFUL, whereupon the best admitted combination
is locked as v2.0."**

Owner decision 57 already ruled on this exact contingency: because the efficiency line was
prioritised and the default-plan combination arm (program cell B5) has **not** flown, *"if decision
30's third consecutive NEUTRAL/HARMFUL one-factor cell fires before the plan arm has flown, v2.0 is
**provisionally** locked on B5e plus the normaliser node (63.78 / 81.85, node applied at delivery)
with the plan-arm replicate owed before the lock is final."* That is the state this verdict leaves
the program in. The lock itself is the coordinator's and the owner's act, not this read's.

Two facts the lock decision should carry. First, this is the **first** of the three streak cells with
no measured loss anywhere: B7a v2 and B4a v2 both put a negative point estimate on at least one axis,
while every metric here is positive. Second, what fails is width, not direction -- the same pattern
that closed B5e on 2026-09-18 and B7a v2 on 2026-09-19. Three consecutive cells decided by CI95 width
on a 1,080-row roster is itself evidence about the roster's resolution, not only about the
mechanisms; that observation is recorded, and no change to any rule is proposed here.

## What is NOT claimed

* **No superiority, generalization, paper-scale or held-out claim.** TRAIN Fold A is an exposed
  discovery roster and every claim of this cell stops at it. Fold B, DEV-1000 and the test split stay
  untouched and unread. Under owner decision 28 these are development numbers and are never compared
  with a published TEST baseline.
* **No admission.** Conjunct 1 fails. The positive movement is *recorded*, never claimed as proven.
* **Nothing about kept versus flown rows.** The recipe forbids conditioning any number on custody,
  and no number here is.
* **No claim that the Reviewer *acts* on the block.** The 101 executed revisions and the flagged-row
  concentration are consistent with it and are not proof of it; whether the Reviewer's criticism
  changed because of the audit, or for some other reason, is not separable here.
* **No attribution to one flag.** The four move together; the per-flag table is a diagnostic.
* **No claim that a retained finite-completion or ReAct-exhausted row is comparable to an
  uninterrupted one.**
* **No claim of downstream request byte identity** (see the wire-identity section).
* **No claim that the block's cost is free.** It is +457.5 prompt tokens on the Reviewer's median
  contact and, through the revisions it provokes, +7.14 % contacts and +13.53 % GPU hours.
* **Nothing about the retired Node Context Policy L1 stack.** This cell's `sealed-draft` attachment
  (item E19) never depended on it.
* **No change to the decision rule, the margins or the estimator**, and no second read: this cell was
  read exactly once.

## Products

All under `SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1`.
`README.md` there hashes every input, every output, the driver and the two single-purpose scripts.

| file | SHA-256 | recipe name |
| --- | --- | --- |
| `paired-v1.json` | `ccf173ddc33387896aeddf698d3e9351096e8f313441f5db1d99b5bf547f8f2e` | `output.files[0]`; alias `score-contrasts.json` |
| `per-scenario-v1.json` | `756f7931e6e7a0ca32e8906bef55cba551c10adf1064c5da77c750b6563c3c48` | `output.files[1]`; alias `per-scenario-tables.json` |
| `diagnostics-v1.json` | `bedef9c56bb1a5295d559bf8933c47b524056f1429907f9aa1144b459db27737` | `output.files[2]`; alias `flight-diagnostics.json` |
| `resume-custody.json` | `03879d17bc92918599b5430c7392abee21d77930c56e362e0649e75699e4ab6c` | the I7r custody proof |
| `wire-identity.json` | `72db706fe27e1531a02aa0a6d04e80daa67c73db96232f8e84ae0de2d52545cd` | per-role request byte identity |
| `monitor-windows.json` | `f2afd8ee01e7de62cb9777bb725214c76f4ba76d1a9d36869370ff0e93d90ffd` | the resume and aborted GPU windows |
| `reviewer-parse-rate.json` | `bd45a73197f8c910ca729eb469014e4a2edff4768769a5069c17311b5e671cb1` | continuity diagnostic |
| `b8ba_paired_read.py` | `2debf09e6c32b43ed30b82ed570ba3c13bfcdf752d7795c7c36252f0ab0d9b18` | the driver |
| `README.md` | (hashes this verdict, so it is not hashed back here) | inputs, outputs, driver, brief-versus-recipe disagreements |

### Where this read and its spawn brief disagreed (the recipe wins)

1. **Resampling.** The brief asked for the precedent cells' whole-speaker cluster bootstrap at seed
   20260915; this recipe registers the **paired per-row bootstrap at seed 20260919**. The per-row
   interval decides. The clustered interval was computed in the same pass and is carried above,
   marked unregistered; it changes no conclusion -- its SLU CI95 is [-0.45, +2.17], likewise
   straddling zero.
2. **Kept-versus-flown strata.** The brief asked for every primary and guard reported separately on
   the kept 378 and the flown 702. The resume recipe forbids exactly that, in those words. The
   custody counts, the kept-id hash and the I7r proof are reported; **no metric is split**.
3. **Names.** The recipe names this file
   `docs/results/2026-09-19-slurp-b8b-anchor-reviewer-audit-verdict.md` (the brief proposed a
   2026-09-20 name "or the recipe's name") and names the three JSON products above; the brief's
   names exist as byte-identical aliases.
