# Cells B4a, B4b and B4c on the sealed anchor: the SLURP v2 ORG knowledge cells, preregistration

Status: **PREREGISTERED BEFORE CONTACT.** Author: the B4 re-base agent, worktree
`/home/chao/saea-worktrees/fable-b4-anchor-prep`, branch `fable/b4-anchor-prep`, base commit
`bd04f4b9`, registration commit `d4965c5e` (every config, plan and ledger row these cells fly).
Authority: `docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md` section 3 (modules
M4a and M4b) and section 4 (Phase B, cells B4a and B4b), the added separation cell B4c, the named
fixes of `docs/results/2026-09-17-slurp-a3-coverage-confusion-audit-v1.md`, the released store
revisions of `docs/readiness/2026-09-17-slurp-semantic-store-revisions-v2-review.md` with their pins
in `docs/readiness/2026-09-17-slurp-semantic-store-release-pins-v2.json`, and owner decisions 6 to 9
of 2026-09-17 in `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`. This document
grants no model contact; all five cells stay readiness `held` until the coordinator flips them.

Everything recorded here was produced with **zero model, tokenizer, encoder, ASR, scorer and server
contacts**. The resident service was never started, stopped or queried, and no worker, campaign,
smoke or FIT was run.

## 0. Why this package exists: the base moved

The review-off v1 package of these same three cells
(`docs/readiness/2026-09-17-slurp-b4-org-cells-v1-preregistration.md`) extended **cell B0**, the
review-loop-off base, and named cell B0 as its primary comparator. On 2026-09-17 module M0 was
**re-decided HARMFUL** under the TRAIN A own null: the replicate B0r reproduced cell B0's request
bytes exactly, the own null measured **h_SLU = 1.1218 pp** and **h_intent = 1.0051 pp** at CI95, and
the intent clause failed on both passes. The Reviewer/Planner loop therefore stays in the default
plan and every later cell builds on the **sealed dual-store anchor**
(`configs/baseline/slurp-native-dual-store-train-fold-a-anchor-v1.json`, review loop on, nominal 5
contacts per row, program ceiling 11).

This package is that re-basing. The v1 package is **superseded before contact**: it never flew, its
ten exposure rows stay `consumed = no`, and each of them now carries a supersession note naming this
document. The moved ORG channels, the questions, the metrics, the diagnostics and the claim boundary
are identical on either base; what changed is the base, the comparators, the margins, the budgets
and every hash.

## 1. Questions

- **B4a.** Does a standing `general_quirky` fallback hypothesis, together with the one-directional
  qa/general contrast the revised intent cards carry, raise intent accuracy -- especially in the
  `general` scenario -- without harming SLU?
- **B4b.** Does the date/time/omission-type slot-contract revision reduce date omission and time
  representation loss and raise pooled SLU?
- **B4c.** If B4a admits, which half carried it: the store revision, or the fallback hypothesis?

The A3 audit bounds what each fix can touch, and these are ceilings, never predictions: FIX-1 34
rows (all 34 gold-`general_quirky` rows whose candidate set never contains the gold id, 25 of them
carrying no `general_*` candidate at all, 28 persisting across all three sealed arms), FIX-2 11 rows
(gold `general_quirky` delivered as `qa_*`; zero in the reverse direction), FIX-4 81 rows (81 of 135
gold-date rows emit no date, 64 of them with the intent already correct), FIX-5 46 rows (46 of 72
rows emit a non-exact time filler; only 8 of 76 gold time mentions are exact).

## 2. Arms

| role | identity |
| --- | --- |
| B4a | `SAEA-SLURP-NATIVE-FALLBACK-QUIRKY-INTENT-V2-ANCHOR-TRAIN-FOLD-A-V2` / `attempt-slurp-native-fallback-quirky-intent-v2-anchor-train-fold-a-generation-v2`, cell `slurp-native-fallback-quirky-intent-v2-anchor-train-fold-a-v2`, composed `a07e895cf893bf2a8ba348449e949f3b0db18808d4435a3670ef49fa37f452d2`, protocol `2577e3c90ab1ac7b90819926ae931fb008dc92f0aaaa26e44917dd55135702ee` |
| B4b | `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-V2` / `attempt-slurp-native-slot-store-v2-anchor-train-fold-a-generation-v2`, cell `slurp-native-slot-store-v2-anchor-train-fold-a-v2`, composed `8d207b33fa7643b7e5acc4ccbd03354fe9c09df09563544c4879c4bb97ee6a4d`, protocol `567a87ad234bb4f17c4735f94219a82b05b25a19d81fdf1ee32bb93b6eda346a` |
| B4c | `SAEA-SLURP-NATIVE-INTENT-STORE-V2-ANCHOR-TRAIN-FOLD-A-V2` / `attempt-slurp-native-intent-store-v2-anchor-train-fold-a-generation-v2`, cell `slurp-native-intent-store-v2-anchor-train-fold-a-v2`, composed `bdbe70349eb324d43b270d05a344386bf5089894ea354fad88009c67774b0e3c`, protocol `7bf967c3f914acc1fb1dd4a3366c863eb6ed1056ef3fec105f4a96efabb4ad9a` |
| comparator, primary | sealed bytes of `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1`, score SHA-256 `7360876322488e5fda689fcafda00e90da2ebf559e5a35e635c550f940202b47`, run manifest `049ac230e536bc6c8fe45bc847756ba486c4904e9c7602c698157f78d70c0152`, official aggregate pooled SLU-F1 48.53 / intent 77.96 / scenario 84.81 / action 79.26 / span 29.50 |
| comparator, secondary | sealed bytes of the released TRAIN A direct anchor `SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-SOURCE-RECOVERY-V1`, score SHA-256 `7840a959fe4f43928fda0e0cacfe8c0ee4200116bfcd269bfe3451b59da29c38`, run manifest `546109055a373b358c43d36878c532b95784ee5d73d07f011c5fa3ea3d7ce11e`, official aggregate pooled SLU-F1 33.89 / intent 73.70 / scenario 82.69 / action 75.09 / span 21.10 |

Neither comparator is ever re-flown or re-scored. All arms share the roster
`docs/receipts/rosters/slurp-evo-fold-a-v2.json` (SHA-256
`1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d`), split `SLURP-EVO-FOLD-A-V2`,
split identity `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, role `discovery`,
and the resident session `serving-slurp-native-candidate-five-train-a-np4-v1` (attach only, never
spawn).

Cells B4a and B4b each have a four-row smoke on the four already-exposed TRAIN A engineering rows
(split identity `4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb`): B4a
`SAEA-SLURP-NATIVE-FALLBACK-QUIRKY-INTENT-V2-ANCHOR-SMOKE-4-V2` (composed
`352a97fa4a2f79b80c558381a5483ecd73543a810e40733da5e3ba1498e34d27`, protocol
`e6828a497645f2ec469d22f9d5f05ab50f20bfebf600d1e49a0ba9fdf8f0a8d6`) and B4b
`SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-SMOKE-4-V2` (composed
`c0572352a9b4758a61654f46d06812819da42d3c7cf9611b24a383882b279661`, protocol
`f13ba493375d75a524884f771a6c5d9b410425951b15cccf9d59d1fe76f3cd9c`). **Cell B4c has no smoke of its
own**: its knowledge store, Perception retrieval geometry and prepared-supply inputs are cell B4a's,
so cell B4a's smoke evidence is reusable as B4c's form evidence.

**Owner decision 9 of 2026-09-17: cell B4c flies only if cell B4a admits.** Owner decision 8 fixes
the GPU order B1 -> B2 -> B4b -> B4a -> B4c.

## 3. The one factor per cell, and what it is not

**B4a.** Moved: `knowledge_stores.slot-contracts.candidate_supply.solver.fallback_candidates` and
its mirrored `phase_material.perception.fill_params.fallback_candidates`, both `["general_quirky"]`,
exactly as item E5a expresses them in
`configs/baseline/slurp-native-dual-store-train-fold-a-fallback-quirky-v1.json`; and
`knowledge_stores.intent-boundaries` pinned to `knowledge/slurp/semantic/intent-boundaries-v2`
(release `31eb595b…`, snapshot `8a27424a…`) with `preparation_source_receipts[0..1]` repinned to that
store's release and completion.

The option has **three declaration surfaces** in the code, by design, each at its own consumption
site (`rails.artifact_results` module comment): the Perception phase material (validated against the
legal inventory and deliberately never read into the response format, so the model is never asked to
produce it), the `candidate_supply` site in `rails.knowledge_provider`, and
`native_episode.role_context.params` in `rails.role_context`. **The third is unreachable on this base
too**: the sealed anchor declares no `native_episode.role_context` block -- checked on the fragment
itself, whose `native_episode` carries only `actions`, `episode_id`, `exhaustion_policy`,
`max_revisions`, `roles` and `schema` -- so the Solver's candidate rendering runs through the
`candidate_supply` site. E5a therefore declares exactly the two reachable sites, and so does this
cell.

The append semantics are fixed by
`rails.slurp_intent_hypotheses.append_fallback_slurp_intent_hypothesis_candidates`: the fallback is
added **only when the Perception response's own projected candidates omit it**, **last**, with
`source = "fallback"` and the fixed `DEFAULT_FALLBACK_DISTINCTION` text, and it never displaces,
reorders or repairs a model-proposed candidate. The sealed Perception artifact is untouched.

**B4b.** Moved: `knowledge_stores.slot-contracts` pinned to
`knowledge/slurp/semantic/slot-contracts-v2` (release `f8e42d4f…`, snapshot `d5992bd1…`) with
`preparation_source_receipts[2..3]` repinned. Eight of the fifty-four slot cards change: `date`,
`time`, `media_type`, `transport_type`, `business_type`, `order_type`, `relation`, `event_name`.

**B4c.** Moved: the intent store only. It is exactly B4a minus the fallback option.

**Held identical in all three**, against the sealed anchor: the roster and split, the model fragment
and resident geometry, the promoted EVO-FOLDS-V2 speech packets, the full native episode with its
Reviewer/Planner review loop on (`max_revisions` 1, reviewer `max_iterations` 3, program ceiling 11
contacts), the Reviewer-only task-contract tool authority, Solver-only answer authority, the
candidate contract (3 candidates, 28 total values, 16 per candidate,
`bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1`), the Perception retrieval geometry
(k = 8, tau 0.0, `saea-fuse-associated-values-v1`, `saea-rank-wcos-prior-agree-v1`, the sealed
speech-query segment vectors and the sealed `SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1` facet
vectors), every instruction template, and the scorers. Fold B is absent.

Each cell also carries its own `native_contact_fit` identity, its own speech-feature identity strings
(provenance only, never model-visible) and its own prepared phase supply, none of which is a channel
the model can see.

### 3.1 What actually changes in the request, proved contact by contact

Receipt: `SPEECHRL_DATA_DIR/coordination/slurp-b4-org-cells-anchor-v2/request-channel-proof-v1.json`
(SHA-256 `3598de1aa75e73eadf8814f5e5889a0447806c348e2f5b1c41473d179cea3102`).

The proof is stronger than the v1 package's. `core.model.transport` renders each
`supplied_evidence` item as `[evidence <evidence_id>] <content>`; the `evidence_id` is
store-qualified and carries no snapshot digest, and `source_uri` is never sent. Those items **are**
the knowledge channel of the wire request. All **5,417** of the sealed anchor's `MODEL_REQUEST`
payloads were read from the run's own trace, every card was reproduced from the released v1 snapshot
(**0 mismatches, 0 unknown evidence ids -- every sealed byte re-derived**), and the v2 card texts
were substituted in place.

*Perception.* The first-phase supply is a prepared artifact of ordered facet ids. All five B4
artifacts carry a **byte-identical `output` block** to the sealed anchor preparation's (`ba5e1faa…`
for the three full cells, `512583ec…` for the two smokes, whose four rows also match the anchor's own
rows for those sample ids), so the **selected facet ids are the anchor's on every one of the 1,080
rows**. Receipt `phase-supply-vs-anchor-v1.json` (`ae0b1082…`). Because the rendered value text is a
function of the bound snapshot and the facet id:

- **B4b: the Perception request is byte-identical to the anchor's on 1080/1080 contacts.**
- **B4a and B4c: 701 contacts byte-identical, 379 differing, and on every differing contact the
  difference is exactly the revised intent card texts.** Rows by number of revised cards selected:
  0 → 701, 1 → 258, 2 → 86, 3 → 26, 4 → 9, 5 → 0. The knowledge byte delta runs 0 to +1,772.

*Reviewer, Planner and Solver.* Supply never rides the control turn; it travels the successor
`QueryState` as typed content blocks (`rails.controllers` module docstring, "Traced supply"). The
anchor declares explicit phase supply only for Perception and candidate supply only for the Solver,
so **no other selection channel exists**: every card in a Reviewer, Planner or later Solver request
was selected by one of those two channels. Measured over the anchor's realized contacts, with the
store revision alone:

| cell | phase | contacts | byte-identical | differing | delta min / max | changed card ids |
| --- | --- | ---: | ---: | ---: | --- | --- |
| B4a, B4c | perception | 1,080 | 701 | 379 | 0 / +1,772 | the 5 revised intent cards |
| B4a, B4c | reviewer | 2,167 | 1,403 | 764 | 0 / +1,772 | the 5 revised intent cards |
| B4a, B4c | planner | 1,085 | 703 | 382 | 0 / +1,772 | the 5 revised intent cards |
| B4a, B4c | solver | 1,085 | 703 | 382 | 0 / +1,772 | the 5 revised intent cards |
| B4b | perception | 1,080 | 1,080 | 0 | 0 / 0 | none |
| B4b | reviewer | 2,167 | 66 | 2,101 | 0 / +3,302 | the 8 revised slot cards |
| B4b | planner | 1,085 | 33 | 1,052 | 0 / +3,302 | the 8 revised slot cards |
| B4b | solver | 1,085 | 33 | 1,052 | 0 / +3,302 | the 8 revised slot cards |

On every one of those contacts the changed set is a subset of the thirteen revised card ids; nothing
else moved.

*The Solver's slot selection is store-version invariant.* The v2 slot store changes no intent
binding (all 402 preserved; the two rebuilt indexes are equal), so for **every** possible Perception
response the Solver receives the same ordered slot value ids: checked exhaustively over all **34,220**
legal three-candidate combinations, **0 disagreeing**. Independently, the anchor's own realized
Solver slot ids were reproduced exactly from its sealed Perception responses on **1080/1080** rows.

### 3.2 Named covariate for cell B4a, measured on the anchor's own candidate distribution

Receipt: `fallback-supply-covariate-v1.json` (SHA-256
`f79017bf601e3568a95de80a74bce60030b930cab5f6a495b22c989ccb96fbec`).

`general_quirky` binds **16 of the 54 released slot cards** -- `artist_name`, `business_type`,
`date`, `device_type`, `drink_type`, `event_name`, `food_type`, `meal_type`, `media_type`,
`movie_name`, `news_topic`, `person`, `place_name`, `relation`, `time`, `timeofday` -- exactly at the
base's `max_values_per_candidate` bound of 16, and identically in v1 and v2.

The v1 package bounded the covariate by enumerating legal triples uniformly. This package measures
it on the anchor's **realized** rows instead, which is what the cell will actually meet:

- `general_quirky` was already among the model's candidates on **17 of 1,080** rows; on the other
  **1,063** the fallback would be appended.
- Without the fallback the model's own three candidates deliver a **median of 12** of the 28
  permitted values (mean 11.80, min 2, max 21); with it, a **median of 20** (mean 20.48, max 27).
- Appending the fallback **adds a median of 8 cards** (mean 8.67, min 3, max 15) and **displaces 0**
  (max 0 over all 1,063 rows). The delivered total never reaches `max_total_values` = 28.
- In bytes, cell B4a's Solver knowledge block grows by a **mean of 15,956 and up to 32,364 bytes**
  per contact against the anchor (reviewer mean 15,969, planner mean 15,956). This is far larger
  than the reachable-ceiling delta of section 8, because the anchor's rows sit well below the
  28-value cap; both readings are true and the verdict must quote this one.

**This is a real second channel and the verdict must not confuse it with the fallback hypothesis
itself.** Cell B4a moves two things at once: the candidate list gains one explicitly labelled
fallback hypothesis, and the Solver's slot-card supply grows by about 16 KB on a typical row. The two
instruments that separate them are cell B4c (the store revision alone) and each row's own selection
audit (`candidate_ids_without_fallback`, `candidate_sources`), which the verdict must report; neither
is a substitute for the other.

**One correction to the v1 wording.** On this base the appended fallback is a **consumption-side
candidate only**: the Solver's history carries the sealed Perception artifact, which is never
rewritten, and every `supplied_evidence` item is a store card, so the fixed
`DEFAULT_FALLBACK_DISTINCTION` text is **not rendered into any request**. The fallback's entire
request-visible effect is the extra slot cards it pulls in; its presence is visible only in the run's
own selection audit. The v1 package described the distinction text as reaching the Solver; that is
corrected here and the smoke acceptance criteria below are worded accordingly.

## 4. Metrics

**B4a primary: intent (joint scenario+action) accuracy**, natural mixture, with official pooled SLU
micro F1 as the non-inferiority guard. FIX-1 and FIX-2 are candidate-coverage fixes whose whole reach
is intent; pooled SLU can move only through the intent that selects the slot contract, so intent is
the estimand this cell is powered for.

**B4b and B4c primary: official pooled SLU micro F1** from `slurp-slu-official-train` (pinned
official `evaluate.py`, `slurp-official-8eb16545`), natural mixture, one complete score per manifest
through `core.scoring_batch`, never sharded, with intent as the guard.

Secondaries for every cell: intent accuracy, scenario accuracy, action accuracy, official pooled span
F1, plus per-row mean official SLU-F1 and per-row mean exact slot F1 and the saves/harms/ties table
with the exact two-sided McNemar p. **Projection v3 is reported beside every official number** (owner
decision 7); the anchor's v3 reading is SLU 51.99 / intent 79.35 / scenario 85.46 / action 80.65 /
span 40.30, and the released direct anchor's is 34.31 / 75.37 / 84.17 / 75.93 / 23.24.

Mandatory diagnostics:

- **B4b**: per-type date and time false negatives and false positives against the A3 baseline (81 of
  135 gold-date rows omitting; 46 of 72 time rows non-exact; 8 of 76 time mentions exact), and the
  same counts for `media_type`, `transport_type`, `business_type`, `order_type`, `relation` and
  `event_name`, reported per type beside the pooled span F1.
- **B4a and B4c**: `general` scenario intent accuracy against the A3 baseline of 36.7 %; candidate
  coverage with and without the appended fallback (A3 baseline 86.8 % overall, 43 % on `general`);
  the number of rows on which the fallback was appended and the share of those on which
  `general_quirky` was then delivered; the gold `general_quirky` → `qa_*` confusion count against the
  A3 baseline of 11 and the reverse direction, which was zero.
- **B4a**: the realized per-row slot-card supply delta of section 3.2, from each row's own selection
  audit.

`delta = arm minus the sealed anchor`, in percentage points; a negative delta means the arm is worse.

## 5. Resampling and tables

Paired whole-speaker cluster bootstrap, **10,000 draws, seed 20260915**, CI95 for advancement and
CI90 for diagnostics, both as percentile pairs of the same retained replicate sequence. Sensitivity:
paired scenario-stratified row bootstrap, same draws and seed. Every verdict carries the per-scenario
table over all 18 scenarios in both the natural-mixture and the equal-scenario weighting, the
equal-scenario delta reported beside the natural-mixture point estimate and never replacing it.
Speaker clusters come from the released roster metadata (125 speakers, 18 scenarios of 60 rows, 523
headset and 557 far-field rows).

## 6. Decision rule (fixed here, before contact)

Null half-widths are the **TRAIN A own null measured by cell B0r** on this exact roster and geometry,
not the imported DEV-1000 margins the v1 package used: **h_SLU = 1.1218 pp**, **h_intent = 1.0051 pp**
at CI95 (0.9420 / 0.8505 at CI90).

**B4b and B4c.**

- **ADMITTED** if the CI95 lower bound of the pooled SLU delta against the sealed anchor is greater
  than 0, intent is non-inferior within 1.0051 pp, the projection-v3 reading agrees in sign, and no
  scenario loses intent beyond the null band.
- **NEUTRAL** if no gate is breached but the CI95 lower bound of the pooled SLU delta is not above 0.
  A neutral module enters the default plan only if it lowers cost; neither cell does, so NEUTRAL
  means not adopted.
- **HARMFUL** if the CI95 lower bound of the pooled SLU delta is at or below −1.1218 pp, or of the
  intent delta at or below −1.0051 pp, or a scenario loses intent beyond the null band.

**B4a, explicitly different.** The primary is the **intent gain**: **ADMITTED** if the CI95 lower
bound of the intent delta against the sealed anchor is greater than 0, **pooled SLU is non-inferior
within 1.1218 pp**, the projection-v3 reading agrees in sign, and no scenario loses intent beyond the
null band. NEUTRAL and HARMFUL are the mirror images, with the same two margins.

**The scenario null band, defined here because v1 left it undefined.** A scenario loses intent beyond
the null band when the CI95 upper bound of that scenario's own paired intent delta is below zero.
Roster-level scenario and action margins remain diagnostics for the per-scenario table, exactly as
cell B0 registered them, not gates.

**The agreement scorer.** Projection v3 (`slurp-slu-official-projected-v3-train`) is the agreement
reading: owner decision 7 of 2026-09-17 makes it the fixed post-processing of every official number.
The symmetric-normalised scorer `slurp-slu-f1-normalized-v1` **cannot** serve on this roster -- it
resolves gold from the SLURP `devel` split and refuses TRAIN sample ids, exactly as cell B0r
recorded -- so the v1 package's "symmetric-normalised scorer agrees in sign" clause is replaced by
the v3 agreement clause. This is recorded as a deviation rather than silently dropped, and the
coordinator may instead register a TRAIN sibling of the symmetric scorer before launch.

No repeat-to-pass: each verdict is read once, from the single official score of the complete manifest.

An admitted B4a does **not** attribute the gain to the fallback hypothesis: that attribution requires
cell B4c and the per-row selection audit of section 3.2.

## 7. Cost reporting (mandatory in every verdict)

- actual generation contacts, against the anchor's realized 5,417 (5.016 per row) and the registered
  ceiling of 11 per row, 11,880 per full cell;
- contacts per row, against the anchor's 5.016 -- these modules add prompt volume, not contacts;
- actual repeated speech seconds, against the anchor's realized 15,459.76 and the registered ceiling
  11 × 3,084.528 = 33,929.8, registered as 33,930;
- actual FIT endpoints, expected 4 per realized contact, ceiling 47,520 per full cell;
- actual native task-contract tool calls, ceiling 6,480 per full cell;
- GPU hours read from the serving monitor
  (`SPEECHRL_DATA_DIR/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl`) over
  the lease window, never a wall-clock guess, against the anchor's measured 3.388;
- mean latency, slot occupancy and duty cycle from the same monitor;
- the prompt-token delta against the anchor, from the cell's own sealed native contact-fit receipts.

Registered ceilings per full cell, which are bounds and not targets: 11,880 generation calls, 47,520
FIT endpoints, 33,930 repeated speech seconds, 12.0 fit-inclusive GPU hours, 6,480 native
task-contract calls, one official complete scoring job, zero ASR, encoder and paid-API calls. Per
smoke: 44 generation calls, 176 FIT endpoints, 117 repeated speech seconds, 1.0 GPU hours, 24
task-contract calls, zero scoring jobs.

## 8. Prompt fit

Receipt: `prompt-fit-v1.json` (SHA-256
`68b42607aaa5d58454e0ba33a5eeb142281b6c48bec51561809e101cb7ef941f`). Slot 24,576 tokens.

Model-free estimate from `core.flight.cli check` over the widest request each phase renders across
the whole roster, decision **ALLOW** for every phase of every cell: B4a and B4c perception 19,553
required window tokens (margin 5,023), reviewer 19,416 (5,160), planner 19,356 (5,220), solver 19,596
(4,980); B4b perception 19,992 (4,584), reviewer 19,856 (4,720), planner 19,795 (4,781), solver
20,035 (4,541). That estimate unions every candidate envelope and is deliberately conservative.

The measured truth comes from the anchor's **5,417 sealed native contact-fit receipts**, which give
each realized contact its own `required_tokens`. The anchor's maxima are perception **4,270**
(minimum margin 20,306), reviewer **15,374** (9,202), planner **15,382** (9,194) and solver **13,482**
(11,094), all fitting. Adding each contact's own knowledge word delta under the repository's stated
proxy (`analysis.slurp_slot_vocabulary.TOKEN_PROXY_FACTOR` = 1.3):

| cell | perception bound / margin | reviewer bound / margin | planner bound / margin | solver bound / margin | worst margin |
| --- | --- | --- | --- | --- | ---: |
| B4a | 4,458 / 20,118 | 17,319 / 7,257 | 17,327 / 7,249 | 15,427 / 9,149 | **7,249** |
| B4b | 4,270 / 20,306 | 15,867 / 8,709 | 15,875 / 8,701 | 13,975 / 10,601 | **8,701** |
| B4c | 4,458 / 20,118 | 15,475 / 9,101 | 15,483 / 9,093 | 13,583 / 10,993 | **9,093** |

Every bound fits on every one of the 5,417 contacts, with at least 7,249 tokens of margin. Cell B4a's
worst case is the appended fallback's largest realized card set (+4,523 words on one contact), not a
union of unreachable worst cases.

The **reachable ceiling** over every legal candidate set is a different, much smaller number, because
the same 28-value cap binds it: the anchor's Solver knowledge block can reach at most 52,062 bytes /
7,262 words, and the ceiling rises by only **615 bytes / 135 words** for B4a and **3,008 bytes / 442
words** for B4b (receipt `solver-knowledge-ceiling-v1.json`, `a913801b…`). The ceiling and the
per-contact delta of section 3.2 cannot co-occur; both are recorded and the verdict must not quote
the ceiling as if it were the typical delta.

This is a bound, not a measurement on the flight tokenizer: each flight fits every realized request
itself through `build_native_contact_fit_gate`, and the coordinator reads those receipts.

## 9. Failure rule

The first failure stops the cell and preserves everything. No automatic restart, replay, row
filtering, roster, role-graph, prompt, geometry or cap change, and no silent recovery. At most one
root-diagnosed recovery re-registration per cell; a second failure closes that flight and the fix must
be proven on a four-row dry run before another mechanism is admitted. A failed four-row smoke stops
its cell until the fix is proven on that same four-row roster. One experiment in flight at a time.

## 10. What is NOT claimed

- No superiority, generalization, paper-scale or held-out claim. TRAIN Fold A is an exposed discovery
  roster.
- No component-causal attribution beyond the one moved channel. Cell B4a moves the fallback candidate
  and the intent store together and can only be decomposed by cell B4c plus the per-row selection
  audit; an admitted B4a alone says nothing about which half paid.
- Nothing about Fold B, DEV-1000 or the test split; they stay unread.
- The A3 row ceilings (34, 11, 81, 46) are upper bounds on what a fix can touch, never predicted
  gains: an appended fallback can still lose selection, and a revised contract can still be ignored.
- Nothing about whether the revised card *language* is better in general; these cells measure one
  frozen core's behaviour on one roster under one retrieval geometry.
- A structural smoke result is never a quality result.
- Nothing about the review loop itself: it is held identical to the anchor in all three cells, and
  its own re-decision is `docs/results/2026-09-17-slurp-b0-review-off-verdict.md` plus the 2026-09-17
  own-null re-decision.

## 11. Analysis recipes

`docs/readiness/2026-09-17-slurp-b4-org-cells-anchor-v2/b4a-analysis-recipe-v1.json`,
`…/b4b-analysis-recipe-v1.json` and `…/b4c-analysis-recipe-v1.json` pin the score artifacts, the
roster metadata (`analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/roster-metadata.json`,
SHA-256 `07f4cd83b83d83d65500a328e0a38421ede575195c63ae118def0d1006c14e34`), the shared estimators
(`analysis.null_calibration_cli.rows_for`, `analysis.null_calibration.pooled_f1`,
`analysis.paired.resampled_statistic`, `analysis.paired.paired_contrast`), the seed, the draws, the
two interval levels, the metric list, the mandatory diagnostics and the decision rule of section 6.
They reuse the released paired-read tooling of the 2026-09-17 TRAIN A direct anchor release rather
than a private reimplementation; `analysis.score_compare_cli` is deliberately not the runner because
it hard-codes CI90 and DEV population names. Both comparator digests are already filled in; only the
arm's own `PENDING_SEAL` / `PENDING_FIRST_OFFICIAL_SCORE` fields remain.

## 12. Registered hashes are pre-flip

Every composed and protocol hash above is the value of the four config fragments **exactly as
committed at `d4965c5e`**: readiness `held`, the preparation requirement present,
`prepared_phase_supply` pinned. `core.config.compose` hashes the whole merged four-fragment document,
so flipping readiness to `ready` and appending the coordinator's own decision requirement each change
the composed hash and therefore the protocol hash. Re-pin with
`core.flight.repin` (the runbook's section 1 gives the exact command) and re-pin this package and the
ten exposure-ledger notes before launch. `core.flight.cli check` confirmed at `d4965c5e` that the
runtime-derived composed and protocol hashes equal the registered ones for all five cells, and that
the method reproduces the sealed anchor's own registered protocol hash
`d1c61c09102dcb8801ea134d763fca0b5b60054d6ef80a3a38752642c107c87d`.

## 13. Pre-contact evidence on file

All under `SPEECHRL_DATA_DIR/coordination/slurp-b4-org-cells-anchor-v2/`, outside the repository so
no receipt can dirty the tree the scoring gate reads. Index: `INDEX-v1.json`.

| receipt | SHA-256 |
| --- | --- |
| `check-b4a-full-v1.json` | `8f8eee0f3e86e8ea21e3074bb15d032013311e849f97fd92854ff83f1f91eb71` |
| `check-b4a-smoke-v1.json` | `76ac22aa48f415aeea34f85f2dbd2bdb6878878770abfddff6e89cd3e3bd812f` |
| `check-b4b-full-v1.json` | `e70cc33d1dba7f2a488385ee2d09f6186a071ae1d7d11d6f77912d5dbd15a9a4` |
| `check-b4b-smoke-v1.json` | `3a64839230a43515446a17ee8808efe6b00b3194909def9dd189eae30d828a83` |
| `check-b4c-full-v1.json` | `793354748d93004c6ff6a48e502356e00590c2bba4bdd4cc82c52d4e16a26d6c` |
| `phase-supply-vs-anchor-v1.json` | `ae0b10821f75491f7dec184daa820d11fe20fa039073b09c5421b00d369261f5` |
| `request-channel-proof-v1.json` | `3598de1aa75e73eadf8814f5e5889a0447806c348e2f5b1c41473d179cea3102` |
| `fallback-supply-covariate-v1.json` | `f79017bf601e3568a95de80a74bce60030b930cab5f6a495b22c989ccb96fbec` |
| `solver-knowledge-ceiling-v1.json` | `a913801b69393239c6f8e924dda2637a49e83ce2d8b33b777ceb2ceb320755aa` |
| `prompt-fit-v1.json` | `68b42607aaa5d58454e0ba33a5eeb142281b6c48bec51561809e101cb7ef941f` |
| `containment-v1.json` | `2c010d4271d385780254b28ba77cbaece3cf2cda32c2c5cbd9bd39a17e5e37df` |
| `composed-hashes-v1.json` | `dfa1315e7a591de76e44d1971a83f86a99fb2aacc6615a18ac2f9c475048ff5f` |
| `plan-hashes-v1.txt` | `4a86970549756d399c8372b40d5e786b4d335526347f79f8bfb50a792f2cd0fa` |
| `ledger-parse-v1.json` | `f37c8d65459234ebb7e3838ec617e5e8d04937dc0a76de703dcdb2734e2d83cc` |

Containment: **0 collisions**, verbatim and casefolded, between the protected material of all four
bound snapshots (`intent-boundaries-v1`/`-v2`, `slot-contracts-v1`/`-v2`; 120 and 108 protected items)
and every one of the five control turns the base sends -- the four role templates and the
task-contract template -- under the runtime rule
`rails.runner._assert_agent_control_excludes_knowledge_payloads` at its floor of 8 characters.

Ledger: `contracts._parse_ledger_tables` sees all ten v2 rows exactly once, each `consumed = no`, and
all ten superseded v1 rows exactly once, each still `consumed = no` and each carrying the supersession
note; 882 rows parsed in total.

`core.flight.cli wire-check` is not declared by any of the five cells, exactly as the sealed anchor,
cell B0 and cell B1 do not declare it: `FlightRuntime._dispatch_phase_program` refuses a native
episode whose transport is not the real shared speech renderer, and `wire_check` installs a text
transport double. The contact-by-contact request-channel proof of section 3.1 is the contact-free
substitute and is stronger per contact, because it reads the real requests the anchor actually sent.

## 14. Deviations from the v1 package

1. **Base, comparators and margins.** The base is the sealed dual-store anchor, the primary
   comparator is the anchor and the secondary is the released direct anchor, and the margins are the
   TRAIN A own null (1.1218 / 1.0051) rather than the imported DEV-1000 margins (1.18 / 0.92).
2. **Budgets.** Eleven contacts per row, so 11,880 generation calls, 47,520 FIT endpoints, 33,930
   repeated speech seconds, 12.0 GPU hours and 6,480 native task-contract calls per full cell; smoke
   44 / 176 / 117 / 1.0 / 24. The `native_task_contract_calls_cap` is newly non-zero because the
   anchor's Reviewer tool authority is reachable here, unlike on the review-off base.
3. **The fallback's request visibility is corrected.** Its fixed distinction text reaches no request
   on this base; only the extra slot cards do. Section 3.2.
4. **The covariate is much larger than the v1 ceiling framing suggested.** On the anchor's realized
   rows B4a's Solver knowledge block grows by a mean of about 16 KB per contact, not the 615-byte
   reachable-ceiling delta. Both numbers are in this package and the verdict must quote the realized
   one.
5. **The agreement scorer.** Projection v3 replaces the symmetric-normalised scorer, which has no
   TRAIN sibling. Section 6.
6. **The scenario null band is now defined.** Section 6.
7. **`phase_tools` is the anchor's own live block**, not the review-off inert one: the Reviewer's
   task-contract authority is reachable and is charged to its own cap.
8. **The smoke reference artifact.** The sealed anchor preparation has no four-row artifact of its
   own, so each smoke's `output` block is compared against the review-off four-row artifact AND, row
   by row, against the anchor's own rows for the same four sample ids; both agree.
9. **No `wire-check` stage** on any cell, for the reason in section 13.
10. **Registered hashes are pre-flip.** Section 12.
