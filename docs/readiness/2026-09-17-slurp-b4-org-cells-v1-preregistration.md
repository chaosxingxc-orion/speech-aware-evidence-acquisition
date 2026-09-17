# Cells B4a, B4b and B4c: the SLURP v2 ORG knowledge cells, preregistration

Status: **PREREGISTERED BEFORE CONTACT.** Author: the B4 preparation agent, worktree
`/home/chao/saea-worktrees/fable-b4-prep`, branch `fable/b4-prep`, base commit `6c5c9ab7`,
registration commit `c622334e`. Authority:
`docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md` section 3 (modules M4a and
M4b) and section 4 (Phase B, cells B4a and B4b), the named fixes of
`docs/results/2026-09-17-slurp-a3-coverage-confusion-audit-v1.md`, and the released store
revisions of `docs/readiness/2026-09-17-slurp-semantic-store-revisions-v2-review.md` with their
pins in `docs/readiness/2026-09-17-slurp-semantic-store-release-pins-v2.json`. This document
grants no model contact; all five cells stay readiness `held` until the coordinator flips them.

Everything recorded here was produced with **zero model, tokenizer, encoder, ASR, scorer and
server contacts**. The resident service was never started, stopped or queried, and no worker,
campaign, smoke or FIT was run.

## 0. The base, and the one thing that blocks every cell

All three cells extend **cell B0**, the review-loop-off base
(`configs/baseline/slurp-native-dual-store-train-fold-a-review-off-v1.json` as committed on
master, with its inert `phase_tools` block and its `native_episode.review_loop: "off"` marker).
Cell B0 is also their **primary comparator**.

**Nothing here may fly before the cell B0 verdict is recorded.** If cell B0 is **HARMFUL**, the
spec's Phase B table is the authority and the coordinator re-bases all three cells on the sealed
anchor `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1` before launch, which means
rebuilding each baseline fragment on the anchor, re-preparing each phase supply, and recomputing
every composed hash, protocol hash, plan hash and exposure-ledger note in this package. If cell B0
is NEUTRAL or better, this package flies as registered.

## 1. Questions

- **B4a.** Does a standing `general_quirky` fallback hypothesis, together with the
  one-directional qa/general contrast the revised intent cards carry, raise intent accuracy --
  especially in the `general` scenario -- without harming SLU?
- **B4b.** Does the date/time/omission-type slot-contract revision reduce date omission and time
  representation loss and raise pooled SLU?
- **B4c.** If B4a admits, which half carried it: the store revision, or the fallback hypothesis?

The A3 audit bounds what each fix can touch, and these are ceilings, never predictions: FIX-1
34 rows (all 34 gold-`general_quirky` rows whose candidate set never contains the gold id, 25 of
them carrying no `general_*` candidate at all, 28 persisting across all three sealed arms), FIX-2
11 rows (gold `general_quirky` delivered as `qa_*`; zero in the reverse direction), FIX-4 81 rows
(81 of 135 gold-date rows emit no date, 64 of them with the intent already correct), FIX-5 46 rows
(46 of 72 rows emit a non-exact time filler; only 8 of 76 gold time mentions are exact).

## 2. Arms

| role | identity |
| --- | --- |
| B4a | `SAEA-SLURP-NATIVE-FALLBACK-QUIRKY-INTENT-V2-TRAIN-FOLD-A-V1` / `attempt-slurp-native-fallback-quirky-intent-v2-train-fold-a-generation-v1`, cell `slurp-native-fallback-quirky-intent-v2-train-fold-a-v1`, composed `814df815488d08c9bd625434eb93323b25ce1e015314342d376f230b4da2457e`, protocol `a2c7ddf9fe18bb819a9ecaf8e743972a0591f394b268a56af501d09678a3318b` |
| B4b | `SAEA-SLURP-NATIVE-SLOT-STORE-V2-TRAIN-FOLD-A-V1` / `attempt-slurp-native-slot-store-v2-train-fold-a-generation-v1`, cell `slurp-native-slot-store-v2-train-fold-a-v1`, composed `9e677170e47f01c3f6eeeae359afde683eef07b7a9cf45a2cdaedecb40c6588a`, protocol `e0e7ad859389bfff488a912fcc617c51db57784e757799cc06cce366d4e952e3` |
| B4c | `SAEA-SLURP-NATIVE-INTENT-STORE-V2-TRAIN-FOLD-A-V1` / `attempt-slurp-native-intent-store-v2-train-fold-a-generation-v1`, cell `slurp-native-intent-store-v2-train-fold-a-v1`, composed `f9635063a5bf745119ab59bc3fd2b84733ae5c3d55de30bec9f564091d5cbab4`, protocol `ed934dcff2d7a6b5d8ae9e6c950324656ab1f1e7aba9d313a2c6be46463ab428` |
| comparator, primary | sealed bytes of `SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-V1` / `attempt-slurp-native-review-off-train-fold-a-generation-v1` (cell B0); score and manifest SHA-256 filled in by the coordinator after B0 finalizes |
| comparator, secondary | sealed bytes of `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1`, score SHA-256 `7360876322488e5fda689fcafda00e90da2ebf559e5a35e635c550f940202b47`, run manifest `049ac230e536bc6c8fe45bc847756ba486c4904e9c7602c698157f78d70c0152`, official aggregate pooled SLU-F1 48.53 / intent 77.96 / scenario 84.81 / action 79.26 / span 29.50 |

Neither comparator is ever re-flown or re-scored. All arms share the roster
`docs/receipts/rosters/slurp-evo-fold-a-v2.json` (SHA-256
`1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d`), split `SLURP-EVO-FOLD-A-V2`,
split identity `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, role `discovery`,
and the resident session `serving-slurp-native-candidate-five-train-a-np4-v1` (attach only, never
spawn).

Each full cell has a four-row smoke on the four already-exposed TRAIN A engineering rows (split
identity `4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb`): B4a
`SAEA-SLURP-NATIVE-FALLBACK-QUIRKY-INTENT-V2-SMOKE-4-V1` (composed
`eeef90e6e8ffdb6d44f802b096d31eb38d60a848a97ee884477edc16cedb56b5`, protocol
`0192634ef738f82c96d698998692a814585e36636e8306642858953280bd629c`) and B4b
`SAEA-SLURP-NATIVE-SLOT-STORE-V2-SMOKE-4-V1` (composed
`d0f44d8cebe9f73980a6d0ecaae4a7bad6da6a8315f95680c7f68496d4a8257b`, protocol
`0088be970c2fdfa3e30189a4e7d77e277557a7966ef89d8fe7ac53e228a4915f`). **Cell B4c has no smoke of
its own**: its knowledge store, Perception retrieval geometry and prepared-supply inputs are cell
B4a's, so cell B4a's smoke evidence is reusable as B4c's form evidence.

## 3. The one factor per cell, and what it is not

**B4a.** Moved: `knowledge_stores.slot-contracts.candidate_supply.solver.fallback_candidates` and
its mirrored `phase_material.perception.fill_params.fallback_candidates`, both `["general_quirky"]`,
exactly as item E5a expresses them in
`configs/baseline/slurp-native-dual-store-train-fold-a-fallback-quirky-v1.json`; and
`knowledge_stores.intent-boundaries` pinned to `knowledge/slurp/semantic/intent-boundaries-v2`
(release `31eb595b…`, snapshot `8a27424a…`) with `preparation_source_receipts[0..1]` repinned to
that store's release and completion.

The option has **three declaration surfaces** in the code, by design, each at its own consumption
site (`rails.artifact_results` module comment): the Perception phase material (validated against
the legal inventory and deliberately never read into the response format, so the model is never
asked to produce it), the `candidate_supply` site in `rails.knowledge_provider`, and
`native_episode.role_context.params` in `rails.role_context`. **The third is unreachable on this
base**: the review-off base declares no `native_episode.role_context` block, so the Solver's
candidate rendering runs through the `candidate_supply` site. E5a therefore declares exactly the
two reachable sites, and so does this cell.

The append semantics are fixed by
`rails.slurp_intent_hypotheses.append_fallback_slurp_intent_hypothesis_candidates`: the fallback
is added **only when the Perception response's own projected candidates omit it**, **last**, with
`source = "fallback"` and the fixed `DEFAULT_FALLBACK_DISTINCTION` text, and it never displaces,
reorders or repairs a model-proposed candidate. The sealed Perception artifact is untouched.

**B4b.** Moved: `knowledge_stores.slot-contracts` pinned to
`knowledge/slurp/semantic/slot-contracts-v2` (release `f8e42d4f…`, snapshot `d5992bd1…`) with
`preparation_source_receipts[2..3]` repinned. Eight of the fifty-four slot cards change: `date`,
`time`, `media_type`, `transport_type`, `business_type`, `order_type`, `relation`, `event_name`.

**B4c.** Moved: the intent store only. It is exactly B4a minus the fallback option.

**Held identical in all three**, against cell B0: the roster and split, the model fragment and
resident geometry, the promoted EVO-FOLDS-V2 speech packets, the candidate contract (3 candidates,
28 total values, 16 per candidate,
`bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1`), the Perception retrieval geometry
(k = 8, tau 0.0, `saea-fuse-associated-values-v1`, `saea-rank-wcos-prior-agree-v1`, the sealed
speech-query segment vectors and the sealed `SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1` facet
vectors), every instruction template, the inert `phase_tools` block, the native episode role graph
with its exact two-contact ceiling, and the scorers. Fold B is absent.

Each cell also carries its own `native_contact_fit` identity, its own speech-feature identity
strings (provenance only, never model-visible) and its own prepared phase supply, none of which
is a channel the model can see.

### 3.1 What actually changes in the request, proved row for row

Receipt: `SPEECHRL_DATA_DIR/coordination/slurp-b4-org-cells-v1/request-channel-proof-v1.json`
(SHA-256 `977b00c769c71da728b66d27486fc9a9a7cac34fac799d5e2dcbc88c0a91f71b`).

*Perception.* The first-phase supply is a prepared artifact of ordered facet ids. All five B4
artifacts carry a **byte-identical `output` block** to cell B0's and to the sealed anchor
preparation's (`ba5e1faa…` for the three full cells, `512583ec…` for the two smokes), so the
**selected facet ids are the anchor's on every one of the 1,080 rows**. Because the rendered value
text is a function of the bound snapshot and the facet id:

- **B4b: the Perception request is byte-identical to cell B0's on 1080/1080 rows** (and 4/4 on the
  smoke); no intent card changed.
- **B4a and B4c: 701 rows byte-identical, 379 rows differing, and on every differing row the
  difference is exactly the revised intent card texts**, verified by in-place patching. Rows by
  number of revised cards selected: 0 → 701, 1 → 258, 2 → 86, 3 → 26, 4 → 9, 5 → 0. The
  knowledge-block byte delta runs 0 to +1,772.

*Solver.* Slot cards reach the Solver through `candidate_supply`, whose index maps each intent id
to its slot ids. The v2 slot store **changes no intent binding**, so for **every** possible
Perception response the Solver receives the same ordered slot value ids: checked exhaustively over
all **34,220** legal three-candidate combinations, **0 disagreeing**. Cell B4b's Solver therefore
differs from cell B0's only in the eight revised card texts, by 0 to +3,302 bytes. Cell B4a's
Solver additionally carries the appended `general_quirky` candidate with its fixed distinction
text, plus the slot cards that candidate brings — see the named covariate below.

*Worst-case envelope.* `core.flight.runtime.render_phase_prompt_envelopes` is the prompt-budget
renderer, not a request renderer: it unions worst-case cards and ranks them by size. Its envelope
grows by a **constant** +1,476 bytes (B4a, B4c) and +3,233 bytes (B4b) on every one of the 1,080
rows and all four declared phases, and cells B4a and B4c render byte-identical worst-case
envelopes on 1080/1080 rows because that renderer already unions every candidate's cards. Constant
growth across rows is itself evidence that no row-dependent channel moved. Receipt
`request-envelope-comparison-v1.json` (`236f1c5f…`), per-row digests
`request-envelope-digests-v1.json` (`ae93e09a…`).

### 3.2 Named covariate for cell B4a: the slot-card supply delta

Receipt: `fallback-supply-covariate-v1.json` (SHA-256
`3506b63434b6dc059f58b5b2e1f399d5e638cde7c37cb9d87ed8070955a10076`).

`general_quirky` binds **16 of the 54 released slot cards** — `artist_name`, `business_type`,
`date`, `device_type`, `drink_type`, `event_name`, `food_type`, `meal_type`, `media_type`,
`movie_name`, `news_topic`, `person`, `place_name`, `relation`, `time`, `timeofday` — exactly at
the base's `max_values_per_candidate` bound of 16, and identically in v1 and v2.

Enumerating **all 32,509** legal three-candidate combinations that omit `general_quirky`: the
model's own three candidates deliver a median of 15 of the 28 permitted values, so appending the
fallback **adds** a median of 7 values (mean 7.34, max 16) and **displaces** a median of 0 (mean
0.005, max 3). The delivered total never exceeds `max_total_values` = 28.

**This is a real second channel and the verdict must not confuse it with the fallback hypothesis
itself.** Cell B4a moves two things at once: the candidate list gains one explicitly labelled
fallback hypothesis, and the Solver's slot-card supply grows. The two instruments that separate
them are cell B4c (the store revision alone) and each row's own selection audit
(`candidate_ids_without_fallback`, `candidate_sources`), which the verdict must report; neither is
a substitute for the other.

## 4. Metrics

**B4a primary: intent (joint scenario+action) accuracy**, natural mixture, with official pooled
SLU micro F1 as the non-inferiority guard. FIX-1 and FIX-2 are candidate-coverage fixes whose
whole reach is intent; pooled SLU can move only through the intent that selects the slot contract,
so intent is the estimand this cell is powered for.

**B4b and B4c primary: official pooled SLU micro F1** from `slurp-slu-official-train` (pinned
official `evaluate.py`, `slurp-official-8eb16545`), natural mixture, one complete score per
manifest through `core.scoring_batch`, never sharded, with intent as the guard.

Secondaries for every cell: intent accuracy, scenario accuracy, action accuracy, official pooled
span F1, plus per-row mean official SLU-F1 and per-row mean exact slot F1 and the saves/harms/ties
table with the exact two-sided McNemar p.

Mandatory diagnostics:

- **B4b**: per-type date and time false negatives and false positives against the A3 baseline (81
  of 135 gold-date rows omitting; 46 of 72 time rows non-exact; 8 of 76 time mentions exact), and
  the same counts for `media_type`, `transport_type`, `business_type`, `order_type`, `relation`
  and `event_name`, reported per type beside the pooled span F1.
- **B4a and B4c**: `general` scenario intent accuracy against the A3 baseline of 36.7 %; candidate
  coverage with and without the appended fallback (A3 baseline 86.8 % overall, 43 % on `general`);
  the number of rows on which the fallback was appended and the share of those on which
  `general_quirky` was then delivered; the gold `general_quirky` → `qa_*` confusion count against
  the A3 baseline of 11 and the reverse direction, which was zero.

`delta = arm minus cell B0`, in percentage points; a negative delta means the arm is worse.

## 5. Resampling and tables

Paired whole-speaker cluster bootstrap, **10,000 draws, seed 20260915**, CI95 for advancement and
CI90 for diagnostics, both as percentile pairs of the same retained replicate sequence.
Sensitivity: paired scenario-stratified row bootstrap, same draws and seed. Every verdict carries
the per-scenario table over all 18 scenarios in both the natural-mixture and the equal-scenario
weighting, the equal-scenario delta reported beside the natural-mixture point estimate and never
replacing it. Speaker clusters come from the released roster metadata (125 speakers, 18 scenarios
of 60 rows, 523 headset and 557 far-field rows).

## 6. Decision rule (fixed here, copied from the spec)

Null half-widths from `docs/readiness/2026-09-09-slurp-own-null-replicate-v1-verdict.md`: intent
0.92, SLU micro 1.18, scenario 0.83, action 0.98 percentage points.

**B4b and B4c.**

- **ADMITTED** if the CI95 lower bound of the pooled SLU delta against cell B0 is greater than 0,
  intent is non-inferior within 0.92 pp, the symmetric-normalised scorer agrees in sign, and no
  scenario loses intent beyond the null band.
- **NEUTRAL** if no gate is breached but the CI95 lower bound of the pooled SLU delta is not above
  0. A neutral module enters the default plan only if it lowers cost; neither cell does, so
  NEUTRAL means not adopted.
- **HARMFUL** if the CI95 lower bound of the pooled SLU delta is at or below −1.18 pp, or of the
  intent delta at or below −0.92 pp, or a scenario loses intent beyond the null band.

**B4a, explicitly different.** The primary is the **intent gain**: **ADMITTED** if the CI95 lower
bound of the intent delta against cell B0 is greater than 0, **pooled SLU is non-inferior within
1.18 pp**, the symmetric-normalised scorer agrees in sign, and no scenario loses intent beyond the
null band. NEUTRAL and HARMFUL are the mirror images, with the same two margins.

No repeat-to-pass: each verdict is read once, from the single official score of the complete
manifest. Scenario and action margins are diagnostics for the per-scenario table, not gates.

An admitted B4a does **not** attribute the gain to the fallback hypothesis: that attribution
requires cell B4c and the per-row selection audit of section 3.2.

## 7. Cost reporting (mandatory in every verdict)

- actual generation contacts, expected exactly 2 per row and 2,160 per full cell;
- contacts per row, expected 2.000, unchanged from cell B0 — these modules add prompt volume, not
  contacts;
- actual repeated speech seconds, expected 2 × 3,084.528 = 6,169.06;
- actual FIT endpoints, expected 4 per realized contact and 8,640 per full cell;
- GPU hours read from the serving monitor
  (`SPEECHRL_DATA_DIR/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl`)
  over the lease window, never a wall-clock guess;
- mean latency, slot occupancy and duty cycle from the same monitor;
- the prompt-token delta against cell B0, from the cell's own sealed native contact-fit receipts.

Registered ceilings per full cell, which are bounds and not targets: 2,160 generation calls, 8,640
FIT endpoints, 6,170 repeated speech seconds, 2.0 fit-inclusive GPU hours, one official complete
scoring job, zero ASR, encoder, task-contract and paid-API calls. Per smoke: 8 generation calls,
32 FIT endpoints, 25 repeated speech seconds, 0.2 GPU hours, zero scoring jobs.

## 8. Prompt fit

Receipt: `prompt-fit-v1.json` (SHA-256
`f9292b31d4519c2b14b3c7885e7296127151ae0ec83cdff843cbbd0e24823236`). Slot 24,576 tokens.

Model-free estimate from `core.flight.cli check` over the widest request each phase renders across
the whole roster, decision **ALLOW** for every phase of every cell: B4a and B4c perception 19,551
required window tokens (margin 5,025), reviewer 19,414, planner 19,354, solver 19,594 (margin
4,982); B4b perception 19,990 (margin 4,586), reviewer 19,854, planner 19,793, solver 20,033
(margin 4,543). That estimate unions every candidate envelope and is deliberately conservative.

The measured truth for exactly the two roles these cells render comes from the anchor's 5,417
sealed native contact-fit receipts: `perception:0` required at most **4,270** tokens (minimum
margin 20,306) and `solver:0` at most **13,157** tokens (minimum margin 11,419), over 1,080
contacts each, all fitting. Cell B0 renders the same envelope minus 8 bytes, so those maxima bound
cell B0 too, and each B4 cell is cell B0 plus the measured knowledge bytes of section 3.1. Under
the repository's stated word proxy (`analysis.slurp_slot_vocabulary.TOKEN_PROXY_FACTOR` = 1.3):

| cell | perception upper bound | margin | solver upper bound | margin |
| --- | ---: | ---: | ---: | ---: |
| B4a | 4,629 | 19,947 | 19,353 | 5,223 |
| B4b | 4,270 | 20,306 | 13,794 | 10,782 |
| B4c | 4,629 | 19,947 | 13,157 | 11,419 |

Cell B4a's Solver bound charges the per-row worst case: all sixteen `general_quirky`-bound slot
cards (33,226 bytes / 4,734 words) added on top of cell B0's widest request. That worst case and
the 13,157-token maximum cannot actually co-occur, because both are governed by the same 28-value
cap: over every legal candidate set the Solver's reachable knowledge ceiling rises by only **637
bytes / 135 words** for B4a and **3,008 bytes / 442 words** for B4b (receipt
`solver-knowledge-ceiling-v1.json`, `8a7b0c86…`). The table is therefore the conservative reading.
It is a bound, not a measurement on the flight tokenizer: each flight fits every realized request
itself through `build_native_contact_fit_gate`, and the coordinator reads those receipts.

## 9. Failure rule

The first failure stops the cell and preserves everything. No automatic restart, replay, row
filtering, roster, role-graph, prompt, geometry or cap change, and no silent recovery. At most one
root-diagnosed recovery re-registration per cell; a second failure closes that flight and the fix
must be proven on a four-row dry run before another mechanism is admitted. A failed four-row smoke
stops its cell until the fix is proven on that same four-row roster. One experiment in flight at a
time.

## 10. What is NOT claimed

- No superiority, generalization, paper-scale or held-out claim. TRAIN Fold A is an exposed
  discovery roster.
- No component-causal attribution beyond the one moved channel. Cell B4a moves the fallback
  candidate and the intent store together and can only be decomposed by cell B4c plus the per-row
  selection audit; an admitted B4a alone says nothing about which half paid.
- Nothing about Fold B, DEV-1000 or the test split; they stay unread.
- The A3 row ceilings (34, 11, 81, 46) are upper bounds on what a fix can touch, never predicted
  gains: an appended fallback can still lose selection, and a revised contract can still be
  ignored.
- Nothing about whether the revised card *language* is better in general; these cells measure one
  frozen core's behaviour on one roster under one retrieval geometry.
- A structural smoke result is never a quality result.

## 11. Analysis recipes

`docs/readiness/2026-09-17-slurp-b4-org-cells-v1/b4a-analysis-recipe-v1.json`,
`…/b4b-analysis-recipe-v1.json` and `…/b4c-analysis-recipe-v1.json` pin the score artifacts, the
roster metadata (`analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/roster-metadata.json`,
SHA-256 `07f4cd83b83d83d65500a328e0a38421ede575195c63ae118def0d1006c14e34`), the shared estimators
(`analysis.null_calibration_cli.rows_for`, `analysis.null_calibration.pooled_f1`,
`analysis.paired.resampled_statistic`, `analysis.paired.paired_contrast`), the seed, the draws,
the two interval levels, the metric list, the mandatory diagnostics and the decision rule of
section 6. They reuse the released paired-read tooling of the 2026-09-17 TRAIN A direct anchor
release rather than a private reimplementation; `analysis.score_compare_cli` is deliberately not
the runner because it hard-codes CI90 and DEV population names. The cell B0 comparator digests are
`PENDING_B0_FINALIZE` and the coordinator fills them in.

## 12. Registered hashes are pre-flip

Every composed and protocol hash above is the value of the four config fragments **exactly as
committed at `c622334e`**: readiness `held`, the preparation requirement present,
`prepared_phase_supply` pinned. `core.config.compose` hashes the whole merged four-fragment
document, so flipping readiness to `ready` and appending the coordinator's own decision
requirement each change the composed hash and therefore the protocol hash. Recompute with the
command in the runbook section 1 after every such edit and re-pin this package and the ten
exposure-ledger notes before launch, exactly as cells B0 and B1 did. `core.flight.cli check`
confirmed at `c622334e` that the runtime-derived composed and protocol hashes equal the registered
ones for all five cells.

## 13. Pre-contact evidence on file

All under `SPEECHRL_DATA_DIR/coordination/slurp-b4-org-cells-v1/`, outside the repository so no
receipt can dirty the tree the scoring gate reads. Index: `INDEX-v1.json`.

| receipt | SHA-256 |
| --- | --- |
| `check-b4a-full-v1.json` | `8363c1e3e31ad18c5e21c6463416ce4ca885f1f42f2ccd3522a800c1555d43cf` |
| `check-b4a-smoke-v1.json` | `d5027de47b1fce45945744e56d55f21df3e40f92c4f6bf14d09408a85c289a1a` |
| `check-b4b-full-v1.json` | `65e14965e8542dd9ddeb43375b5be68ceb9074f33db56af1efa57ceb1cb75bba` |
| `check-b4b-smoke-v1.json` | `f13a2c687cbac56f2bd4cbf5d541aa37403d5170f5e909e2ec4e09a6f9185460` |
| `check-b4c-full-v1.json` | `e5d2605cce4ed517bce7458469dcc86c87501dfc3782a2bcbec5d359c6f37430` |
| `phase-supply-vs-base-v1.json` | `f439fc1045e1850522a8776eb6266222cd6a71102503ec46d09927697a09b764` |
| `request-channel-proof-v1.json` | `977b00c769c71da728b66d27486fc9a9a7cac34fac799d5e2dcbc88c0a91f71b` |
| `request-envelope-comparison-v1.json` | `236f1c5fd6a2e17934e68589a63ec304e09b749b9b932144cc64cd89b5428873` |
| `request-envelope-digests-v1.json` | `ae93e09a7bbead9510ecb96c03af80b46c6425786e11bb13cdb64c9bbe4c03ad` |
| `fallback-supply-covariate-v1.json` | `3506b63434b6dc059f58b5b2e1f399d5e638cde7c37cb9d87ed8070955a10076` |
| `solver-knowledge-ceiling-v1.json` | `8a7b0c86e0ee2b62d9add580d13bbabbb003bd0ef3a46566af841421671f4672` |
| `prompt-fit-v1.json` | `f9292b31d4519c2b14b3c7885e7296127151ae0ec83cdff843cbbd0e24823236` |
| `containment-v1.json` | `39ac50e37ebb0c2656049b3cd88587db18e7e8f842810c8468018fb0ce4b540c` |
| `composed-hashes-v1.json` | `c9e3e1a43c9844f9aa75cbfdc9efb5a400cf38af9c9222294b36dba1fc2617bd` |
| `plan-hashes-v1.txt` | `29fd135b3089550ce0e8c679b2f5a8a1855ff5ec713112e639fb40429a909da5` |
| `ledger-parse-v1.json` | `986789123f575fa9c4883e501703c86afad97e328be8d00cf85ef35b85eba135` |
| `wire-check-smoke-v1.stderr.txt` | `c0db5657a42f90a7011ea6c751ce416409e0ffaa0b3994e219fb54e60a6a0fec` |

Containment: **0 collisions**, verbatim and casefolded, between the protected material of all four
bound snapshots (`intent-boundaries-v1`/`-v2`, `slot-contracts-v1`/`-v2`; 120 and 108 protected
items) and every one of the five control turns the base sends — the four role templates and the
task-contract template — under the runtime rule
`rails.runner._assert_agent_control_excludes_knowledge_payloads` at its floor of 8 characters.

Ledger: `contracts._parse_ledger_tables` sees all ten B4 rows exactly once, each `consumed = no`,
864 rows parsed in total.

`core.flight.cli wire-check` is not declared by any of the five cells, exactly as the sealed
anchor, cell B0 and cell B1 do not declare it: `FlightRuntime._dispatch_phase_program` refuses a
native episode whose transport is not the real shared speech renderer, and `wire_check` installs a
text transport double. The stored refusal is the stage-permission refusal that follows from not
declaring the stage. The row-for-row request-channel proof of section 3.1 is the contact-free
substitute and is stronger per row.

## 14. Postscript: the cell B0 verdict landed during preparation

Master advanced from `6c5c9ab7` to `2b960418` while this was being prepared, and
`docs/results/2026-09-17-slurp-b0-review-off-verdict.md` now records cell B0 as **HARMFUL by the
preregistered intent clause**: pooled SLU +0.13 [-1.15, +1.45], intent -0.37 [-1.53, +0.82], with
the intent CI95 lower bound below the -0.92 margin. The verdict calls it a width failure with a nil
point estimate -- every saves/harms table is a tie -- and registers a same-roster own-null
replicate, cell B0r, with a re-decision rule. Cell B0's sealed digests are score
`51f37e6c5a78751f2d000ac370cff6f0fff18745cd18d1fc81a2cd145ce960ae` and run manifest
`8b6f3f783f1933c4009c46cdc01472e240c547a496f7553c07e5efe301cdfe32`.

Section 0's re-basing clause is therefore live but unsettled: the base decision for these three
cells belongs to the B0r re-decision, not to the raw label. This preregistration is unchanged by
either outcome except for which sealed comparator is primary and which base the five baseline
fragments extend; the moved ORG channels, the decision rules, the metrics, the diagnostics and the
claim boundary are identical on either base. Re-basing would require rebuilding the five baseline
fragments, re-preparing the five phase supplies and recomputing every hash in this package, and it
must happen before any contact.

Independently of that decision, master's range touches `rails.knowledge_stores`, which the prepared
phase-supply artifact identity pins, so all five supplies must be re-prepared and re-pinned after
the merge. The registered composed and protocol hashes were verified to reproduce unchanged under
master's `core.config`, and master's new `preparation_source_receipts` validator accepts all five
fragments.
