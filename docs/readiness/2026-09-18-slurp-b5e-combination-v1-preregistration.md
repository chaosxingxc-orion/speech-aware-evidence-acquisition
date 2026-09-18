# Cell B5e: the early combination of modules M1 and M4b on the sealed anchor, preregistration

Status: **PREREGISTERED BEFORE CONTACT.** Author: the B5e registration agent, main checkout
`studies/speech-aware-evidence-acquisition`, base commit `9bfd39e0`. Authority: **owner decisions 18
to 21 of 2026-09-18** (`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`) —
decision 19 names this cell by name, decision 20 fixes what happens if it misses, decision 21 puts
the B4b replicate before it — together with owner decision 1 (the bar), owner decision 7 (projection
v3 as the fixed post-processing of every official number), owner decision 15 (the GPU order) and
owner decision 17 (the per-scenario net-harmed-rows diagnostic). Program:
`docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md`, section 4 (the B5 form and the
bar-first order update), section 5 (the fixed protocol) and section 6 (verification).

This document grants no model contact. Both cells stay readiness `held` until the coordinator mints
the root decision receipt and flips them with `scripts/flights/repin_cell.py`.

Everything recorded here was produced with **zero model, tokenizer, encoder, ASR, scorer and server
contacts**. The resident service was never started, stopped or queried; no run directory was read or
written; the B4b replicate flight in progress was not touched.

## 1. Why this cell exists, and the arithmetic that opened it

Two modules are admitted on this base and no cell has ever run them together.

| module | cell | official pooled SLU / intent | projection v3 SLU / intent | status |
| --- | --- | ---: | ---: | --- |
| — (base) | sealed dual-store anchor | 48.53 / 77.96 | 51.99 / 79.35 | the base every Phase B cell moves against |
| **M1** speech-keyed exemplar supply | B1 recovery arm + twin | 61.14 / 80.19 (**+12.61** / +2.22) | 62.67 / 81.76 (**+10.67** / +2.41) | **ADMITTED** 2026-09-18, owner decision 18 branch A (`docs/results/2026-09-18-slurp-b1-twin-verdict.md`) |
| **M4b** slot store v2 | B4b | 51.09 / 78.52 (**+2.55** / +0.56) | 54.05 / 79.72 (**+2.06** / +0.37) | **ADMITTED** 2026-09-17, provisional until replicated (`docs/results/2026-09-17-slurp-b4b-slot-store-v2-verdict.md`) |

Owner decision 19 states the arithmetic that made this cell jump the queue: **62.67 + 2.06 = 64.73**
in v3 terms, against a bar of 64.00, with intent already 3.76 points above its own bar of 78.00. On
the **unprojected** official numbers the same sum is 61.14 + 2.55 = 63.69, which does **not** clear
64 — so the bar clause of section 7 reads the v3 numbers, exactly as owner decisions 1 and 7
together require, and reports the unprojected number beside them and says out loud whether it clears.

That arithmetic is an *extrapolation*, not a measurement. Two modules that each pay on the same base
need not pay together: M1 supplies twenty annotated exemplars whose own filler surfaces already carry
date and time forms, and M4b revises the date and time slot contracts the Solver reads from the
`slot-contracts` store. They plausibly overlap. **This cell measures the combination once and reads
it once.** Additivity is a reported quantity of section 7, never an assumption of it.

The queue position is owner decision 21's: the B4b replicate flies first, then this cell. Owner
decision 19's consequence chain is fixed before any number is read — meeting the bar registers B5er
(a request-identical replicate) and, on two passes, locks "SLURP base v2.0"; missing it resumes
decision 15's order **without lowering the bar** (owner decision 20).

## 2. Question

Does turning on **both** admitted modules at once — the `train-exemplars` store (M1) and the
`slot-contracts` v2 re-pin (M4b) — on the sealed dual-store anchor base, on TRAIN Fold A 1,080:

1. **meet the program bar** (v3-projected pooled SLU-F1 >= 64.00 and v3-projected intent >= 78.00), and
2. **retain M4b's contribution inside the combination**, measured against cell B1 alone?

## 3. Arms and comparators

| role | identity |
| --- | --- |
| treatment | `SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-V1` / `attempt-slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-generation-v1`, cell `slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-v1`, composed config `220a5ac4381090071d3da31798496a4486de486525c591d2d39e63d4eb0beb9e`, protocol `d33b86abf7be171887262144ad3799e7ed79cde5f4dd3a2aaf42a0e71023b638` |
| smoke | `SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-SMOKE-4-V1` / `attempt-slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-smoke-4-generation-v1`, cell `slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-smoke-4-v1`, composed config `9c5d3c4beec5f5c120a2593a5eaa648c5e76d78d138f3f506508b195f7e45c9f`, protocol `c5cbfa6ae93319bb25531087040dfaa741713b2eefb67c7c30be2fe25e99d61b` |
| **base comparator** | sealed bytes of `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1`, score `7360876322488e5fda689fcafda00e90da2ebf559e5a35e635c550f940202b47`, run manifest `049ac230e536bc6c8fe45bc847756ba486c4904e9c7602c698157f78d70c0152`; official 48.53 / 77.96 / 84.81 / 79.26 / 29.50, v3 51.99 / 79.35 / 85.46 / 80.65 / 40.30 |
| **M1 leg** | sealed bytes of `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2`, score `a7105b328509a8bd00c4678fd076e9be4d242b6189bb82bbd290bd596e3c9078`, run manifest `b07ed553ff9f78b8e3ead6797bb66fb92a1820793b8aa5061576c6f66aa1a8ad`; official 61.14 / 80.19 / 86.39 / 81.39 / 48.43, v3 62.67 / 81.76 / 87.13 / 82.96 / 52.65 |
| **M4b leg** | sealed bytes of `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-V2`, score `751c529806e7cd03db13cfba58d583bf7b9d7f14b5b62b6b26e676a5acb308a1`, run manifest `b3f7e7ac0babd5ae3e764ad93948203cc40192d72ac3a156b4a479cc69c256ea`; official 51.09 / 78.52 / 85.09 / 79.63 / 32.40, v3 54.05 / 79.72 / 85.93 / 80.83 / 41.85 |
| **direct comparator** | sealed bytes of `SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-SOURCE-RECOVERY-V1`, score `7840a959fe4f43928fda0e0cacfe8c0ee4200116bfcd269bfe3451b59da29c38`, run manifest `546109055a373b358c43d36878c532b95784ee5d73d07f011c5fa3ea3d7ce11e`; official 33.89 / 73.70 / 82.69 / 75.09 / 21.10, v3 34.31 / 75.37 / 84.17 / 75.93 / 23.24 |
| **secondary, conditional** | `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-REPLICATE-V2`, the B4b request-identical replicate — **admitted into this read ONLY IF it is sealed before this cell's first contact.** If it is not, it is named here and left out, and its absence is stated in the verdict. It never gates. |

**Every comparator is sealed bytes. None is re-flown, re-scored or re-read for this cell.** All arms
share the roster `docs/receipts/rosters/slurp-evo-fold-a-v2.json` (SHA-256
`1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d`), split `SLURP-EVO-FOLD-A-V2`,
split identity `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, role `discovery`,
and the resident session `serving-slurp-native-candidate-five-train-a-np4-v1` (attach only, never
spawn). The smoke uses the four already-exposed TRAIN A engineering rows every four-row form smoke of
this repository reuses, split identity
`4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb`.

## 4. The two factors, and what they are not

Moved against the sealed anchor's own committed baseline
(`configs/baseline/slurp-native-dual-store-train-fold-a-anchor-v1.json`), in the one channel
`knowledge_stores`:

1. **M1.** `knowledge_stores` gains the named store `train-exemplars`, **byte-for-byte the block the
   B1 recovery arm flew** (`configs/baseline/slurp-native-anchor-exemplars-k20-train-fold-a-recovery-v2.json`):
   release `171aa4a8…`, snapshot `4c498dc0…` over the 9,354-facet construction pool that excludes
   every utterance with a recording in TRAIN Fold A, Fold B or DEV-1000; `phase_supply.solver` plain
   top-k with k = 20, `saea-fuse-supplyfilter-v1` at m = c = top_l = 20,
   `saea-rank-wcos-prior-agree-v1` with w_cos = 1 and w_prior = w_agree = 0, tau 0.0, keyed by the
   row's own sealed Fold A full-utterance speech vector in the `content` dimension. The values reach
   the Solver as typed content blocks on the acquire transition, never as instruction text.
2. **M4b.** `knowledge_stores["slot-contracts"]` is re-pinned from the v1 release/snapshot pair to
   the v2 pair, **byte-for-byte the block cell B4b and its replicate flew**
   (`configs/baseline/slurp-native-anchor-slot-store-v2-train-fold-a-v2.json`): release
   `f8e42d4ff1b220f45b26397340149566544cf5b13d7453fbc46a2b5c3400d11b`, snapshot
   `d5992bd12687cbd0204c14fc4e29f987697b8751321d524d7707229032f5bdec`. `candidate_supply`,
   `store_role` and every other leaf are the anchor's.

**Proved, not asserted.** `tests/unit/test_b5e_combination_config.py` (six tests, model-free) and the
receipt `coordination/slurp-b5e-combination-v1/composed-hashes-v1.json` pin all of it on the
**composed** values, not only on the fragment files:

| claim | value |
| --- | --- |
| composed keys identical to the sealed anchor pair / differing | 48 / 19, and the only model-facing one is `knowledge_stores` |
| composed keys identical to the B1 recovery arm / differing | 52 / 15, and the only model-facing one is `knowledge_stores` |
| composed keys identical to cell B4b / differing | 51 / 16, and the only model-facing one is `knowledge_stores` |
| store ids added against the anchor | exactly `train-exemplars` |
| anchor store ids that moved | exactly `slot-contracts`, in exactly two leaves, `release` and `snapshot` |
| `intent-boundaries` against the anchor | identical |
| `train-exemplars` against the B1 recovery arm | **identical** |
| `slot-contracts` against cell B4b | **identical** |
| both modules turned off | reconstructs the anchor's `knowledge_stores` block exactly |

Everything else that differs is bookkeeping this cell must vary to be a distinct run identity:
`native_contact_fit` (its own FIT run and attempt at the unchanged 47,520-endpoint ceiling), the two
speech-feature identity ids (provenance only), the `preparation_source_receipts` rows (the
slot-contracts-v2 rows in place of the v1 rows, taken verbatim from cell B4b's fragment, plus the
exemplar release receipt row), `prepared_phase_supply`, the two free-English notes, and the
experiment fragment's own `cells`, `date`, `experiment_id`, `fragment_kind`, `failure_policy`,
`generation_budget`, `population`, `purpose`, `execution_plan`, `execution_profile` and
`service_session`.

**Held identical:** the anchor role graph (perception 1, solver 1, **reviewer 3, planner 1,
max_revisions 1**, policy `phase-native-candidates-review-revise-v1`, program ceiling 11 contacts per
row), the roster and split, the model fragment and the resident np4 / 24,576-token geometry, the
promoted EVO-FOLDS-V2 speech packets, the Perception retrieval geometry (k = 8, tau 0.0,
`saea-fuse-associated-values-v1`, the sealed Fold A speech-query segment vectors and the sealed
`SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1` facet vectors), the four-candidate K8 / max 3 / 16 per
candidate / 28 total supply contract, **every instruction template**, the `phase_tools` Reviewer
task-contract authority block, Solver-only answer authority, and the scorers. Fold B is absent.

**The prepared Perception supply does not move.** `prepare-supply` was re-run model-free at **one
worker** on this commit for both cells, and each artifact's `output` is byte-identical to the sealed
anchor's own, to cell B1's and to cell B4b's: `output_sha256`
`ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` on **1,080 of 1,080** rows for the
arm, and `512583ec2c684a2e285bfafea3f4101033a2a1d413fad39c8cfd2b74fbff5733` on **4 of 4** rows for the
smoke. Receipt: `coordination/slurp-b5e-combination-v1/prepared-supply-comparison-v1.json`.

**What this cell is not.** It is not a new mechanism (owner decision 19's naming note: "B5e and B5er
are the B5/B5r form restricted to the modules admitted at the time of registration; none of them is a
new mechanism"). No k, tau, threshold, fuse policy, release or snapshot is tuned. No third module
joins. The review loop is the anchor's and is not ablated.

### The one request-channel difference that is stated rather than measured

`render_phase_prompt_envelopes` accumulates a phase's supply bound in declaration order, so a static
render shows the exemplar blocks only at the Solver. At dispatch the native role episode executes
`perception -> solver -> reviewer -> planner`, and the supplied values stay visible in the accumulated
`QueryState`, so the Reviewer and Planner requests that follow a Solver contact carry the same blocks
— which is exactly what the B1 recovery arm's own smoke measured in flight (the 20 exemplar items
reached every post-Perception request). The `native_contact_fit` gate fits every realized request
immediately before dispatch and is the exact per-request authority; section 9 shows the resulting
worst case clears the slot by more than 6,500 tokens.

`core.flight.cli wire-check` remains unavailable for any native-episode cell, as it was for the
anchor, B0, B0r, B1, B4b and B4b-rep: `FlightRuntime._dispatch_phase_program` refuses a native
episode whose transport is not the real shared speech renderer, and `wire_check` installs a text
transport double.

## 5. Metrics

Primary: **official pooled SLU micro F1** from `slurp-slu-official-train` (pinned official
`evaluate.py`, `slurp-official-8eb16545`), natural mixture, **one complete score per manifest through
`core.scoring_batch`, never sharded**.

Bar reading: **`slurp-slu-official-projected-v3-train`** — owner decision 7's fixed post-processing
of every official number. Symmetric reading beside it: **`slurp-slu-f1-normalized-v1-train`**, the
TRAIN sibling owner decision 14 ordered, which exists on this roster since 2026-09-17
(`docs/results/2026-09-17-slurp-train-symmetric-reread-v1.md`).

Secondaries: intent (joint scenario+action) accuracy, scenario accuracy, action accuracy, official
pooled span F1, per-row mean official SLU-F1, per-row mean exact slot F1, saves/harms/ties with the
exact two-sided McNemar p.

Diagnostics, mandatory in the verdict and never gates:

- **the M1 diagnostics of the B1 preregistration, recomputed on this cell's own sealed outputs**:
  candidate-union coverage realized in the delivered answer against A2's availability number 0.9722
  and against B1's own realized value; the Solver escape-to-neighbour-intent rate; the exemplar token
  volume actually rendered per row; and the revision counts and review-loop dispositions against the
  anchor's 5 executed revisions, cell B1's 7 and the twin's 9;
- **the B4b slot-matching diagnostic**, recomputed on this cell's own sealed outputs with the
  official scorer's own matching: the per-type `date`, `time`, `media_type`, `transport_type`,
  `business_type`, `order_type`, `relation` and `event_name` false-negative and false-positive
  decomposition, and the omission / all-exact / partial / exact-mention / spurious-mention table, each
  read against cell B4b's own first-pass numbers (date omissions 81 -> 77, time omissions 19 -> 13,
  time FN mass -32.86, date FN mass -10.16);
- **owner decision 17's net harmed rows per scenario**, flagging any scenario at five or more, on
  every contrast of section 7;
- **cost and duty cycle** (section 8).

`delta = arm minus comparator`, in percentage points; negative means the arm is worse.

## 6. Resampling and tables

Paired whole-speaker cluster bootstrap, **10,000 draws, seed 20260915**, CI95 for advancement and
CI90 for diagnostics, both as percentile pairs of the same retained replicate sequence. Sensitivity:
paired scenario-stratified row bootstrap, same draws and seed. Every table is reported in **both the
natural-mixture and the equal-scenario weighting**; the equal-scenario delta is reported beside the
natural-mixture point estimate and never replaces it. Speaker clusters (125) and the 18 scenarios of
60 rows come from the released roster metadata
(`analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/roster-metadata.json`, SHA-256
`07f4cd83b83d83d65500a328e0a38421ede575195c63ae118def0d1006c14e34`); 523 headset and 557 far-field
rows.

**STOP condition.** Before any table of this cell is read, all four sealed comparators must reproduce
their registered official and projection-v3 aggregates (section 3) to the hundredth of a point, and
the recomputed `(B1 minus anchor)` and `(B4b minus anchor)` contrasts must reproduce **+10.54** /
**+0.74** and **+1.1294** / **-0.7117** CI95 lower bounds (pooled SLU / intent) to the digit. If they
do not, the read stops: the same sealed bytes under the same estimator and seed cannot give two
answers.

## 7. Decision rule, fixed here before any contact

Own-null margins are the TRAIN A own null measured by cell B0r on this exact roster — the CI95
half-widths of (B0r minus B0): **h_SLU = 1.1218** and **h_intent = 1.0051** percentage points. They
replace the imported DEV-1000 margins, which gate nothing here. Read **exactly once**, from the single
official score of the complete manifest.

> **Clause 1 — the bar clause (owner decisions 1 and 7).** Cell B5e **MEETS THE BAR on this pass** if
> and only if the **v3-projected pooled SLU-F1 is >= 64.00 AND the v3-projected intent
> (scenario+action) is >= 78.00**. The unprojected official numbers and the symmetric-normalised
> numbers are reported beside them, and the verdict states explicitly whether the **unprojected**
> pooled SLU also clears 64.00. Meeting the bar **registers B5er, a request-identical replicate,
> immediately**; "replicated" is B5er's job and is never claimed by this pass (owner decision 1:
> the bar is "replicated on the same roster"). Missing the bar **does not lower the bar** (owner
> decision 20): admission continues in decision 15's order and B5b, the combination of every module
> admitted by then, is read against the same bar.
>
> **Clause 2 — the combination clause.** The combination is **ADMITTED** — that is, **M4b's
> contribution survives inside the combination** — if and only if all three hold: (a) the CI95 lower
> bound of the **(B5e minus B1)** pooled official SLU-F1 delta is **greater than 0**; (b) the
> **(B5e minus B1)** intent delta is **non-inferior at -h_intent**, i.e. its CI95 lower bound exceeds
> **-1.0051**; and (c) **no scenario's paired intent CI95 upper bound against B1 lies below zero**.
> Otherwise the combination is **NEUTRAL**. The symmetric contrast **(B5e minus B4b)** is reported as
> **M1's contribution inside the combination**, with the same three clauses evaluated and reported —
> **it does not gate**.
>
> **Additivity is reported.** `(B5e minus anchor)` is reported with its CI95 against the sum of the
> two single-module deltas: **+12.61 + 2.55 = +15.16** pp official (and +10.67 + 2.06 = +12.73 pp in
> v3 terms). The verdict states whether that sum lies inside the `(B5e minus anchor)` CI95,
> above it (sub-additive, the modules overlap) or below it (super-additive). This is a reported
> quantity and gates nothing.
>
> **Clause 3 — the HARMFUL trigger.** If the **(B5e minus B1)** pooled SLU CI95 **upper** bound lies
> **below -h_SLU = -1.1218**, or its intent CI95 **lower** bound lies **below -h_intent = -1.0051**,
> the combination is **HARMFUL**: the v2 candidate falls back to **B1 alone**, **B5er is not
> registered**, and **the owner is told**.

**Failure rule.** A first failure stops the flight and preserves the attempt — no automatic restart,
replay, row filtering, roster, role-graph, prompt, geometry or cap change, and no silent recovery. **At
most one root-diagnosed recovery re-registration**; a second failure closes the cell and the fix must
be proven on a four-row dry run before another mechanism is admitted. A partial manifest is never
scored and never read. One experiment in flight at a time.

**Smoke acceptance is structural only**: five contacts per row on the anchor's own trajectory
statistics (11 is the ceiling), the exemplar supply acquired **exactly once per row**, the v2 slot
cards present in the Solver evidence, every request fits (`every_request_fits = true` on one
`*.request-fit.json` per realized contact), and the manifest seals. No answer, reference or quality
interpretation, and no scorer.

## 8. Cost

Registered ceilings per full cell, which are **bounds and not targets**: **11,880 generation calls,
47,520 FIT endpoints, 33,930 repeated speech seconds, 12.0 fit-inclusive GPU hours, 6,480 native
task-contract calls, one official complete scoring job, zero ASR, encoder and paid-API calls.** The
generation ceiling is the exact program maximum on this role graph,
`1 + (max_revisions + 1) * (reviewer 3 + planner 1 + solver 1) = 1 + 2 * 5 = 11` contacts per row
times 1,080 rows; the FIT ceiling is `1,080 * 11 * (1 speech packet + 3 endpoints)`. They are cell
B1's own registered ceilings, unchanged. Smoke ceilings: **44 generation contacts, 176 FIT endpoints,
117 repeated speech seconds, 1.0 fit-inclusive GPU hours, 24 native task-contract calls, zero scoring
jobs** — cell B1's recovery smoke's own, unchanged.

**Expected** spend, from the four sealed realisations on this geometry (anchor 5,417 contacts /
3.388 GPU-h; B4b 5,407 / 3.465; B1 arm 5,425 / 3.682; B1 twin 5,429 / 3.637): about **5,400 contacts
at about 5.0 per row and about 3.7 GPU hours**, plus about 3 minutes of official scoring. Both
modules add prompt tokens, never contacts.

Mandatory in the verdict: actual generation contacts and contacts per row (against 5,417 / 5,407 /
5,425 / 5,429); actual repeated speech seconds (against 15,459.76 / 15,432.81 / 15,494.60); actual FIT
endpoints and the minimum fit margin (against B1's 8,600 and B4b's 8,242); actual native task-contract
calls (against 1,082 / 1,075 / 1,084); prompt and completion tokens (against the anchor's
45,998,267 / 255,153, B1's 49,388,949 / 255,524 and B4b's +2.59 %); GPU hours read from the serving
monitor (`SPEECHRL_DATA_DIR/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl`)
over each lease window, never a wall-clock guess; mean latency, slot occupancy, utilisation and parked
fraction from the same monitor; preprocess and official scoring wall time.

## 9. Prompt fit

The 24,576-token serving slot. Recomputed here from the **sealed native contact-fit receipts of the
four 1,080-row cells that have flown this role graph** — 5,417 + 5,407 + 5,425 + 5,429 = 21,678
receipts, all read-only, `every_request_fits = true` in every one
(`coordination/slurp-b5e-combination-v1/prompt-fit-v1.json`, maximum required tokens per role visit):

| role visit | contacts (anchor) | anchor | B4b (M4b) | B1 arm (M1) | B1 twin |
| --- | ---: | ---: | ---: | ---: | ---: |
| perception:0 | 1,080 | 4,270 | 4,270 | 4,270 | 4,270 |
| solver:0 | 1,080 | 13,157 | 13,541 | 14,079 | 13,574 |
| reviewer:0 | 1,080 | 13,259 | 13,643 | 14,198 | 13,676 |
| reviewer:1 | 1,077 | 15,037 | 15,421 | **15,976** | 15,454 |
| planner:0 | 1,080 | 15,028 | 15,409 | 15,946 | 15,427 |
| solver:1 | 5 | 13,482 | 14,447 | 13,812 | 14,970 |
| reviewer:2 | 5 | 13,596 | 14,556 | 13,915 | 15,091 |
| reviewer:3 | 5 | 15,374 | **16,334** | 15,693 | **16,869** |
| planner:1 | 5 | **15,382** | 16,321 | 15,691 | 16,840 |

On the five high-count visits — the only ones whose maxima are statistically meaningful — the module
increments over the anchor are **M1 at most +939 tokens** and **M4b at most +384**. On the four
revision visits (4 to 9 contacts each) the maxima are dominated by *which* rows revised rather than by
the module, which the twin proves directly: it carries the same store as the B1 arm at the same k and
realises +1,495 tokens at `reviewer:3` where the arm realises +319.

**The lesson this package inherits.** The B1 preregistration registered a *realised-sum* upper bound
of **16,465** tokens (anchor widest 15,382 + measured exemplar-block maximum 1,083); its own twin then
realised **16,869**, **404 tokens above it** — still below B1's *static* bound of 17,018, and every
one of the twin's 5,429 requests fit. B4b recorded the same kind of optimism from the other direction
(its model-free proxy put the widest reviewer request at 15,867 and the realised maximum was 16,334).
So this package registers the **static** bound and reports the realised sum only as a cross-check.

> **Registered static upper bound for any B5e request: 15,382 + 1,636 + 965 = 17,983 required tokens,
> a margin of 6,593 against the 24,576-token slot** — the anchor's widest realised role visit, plus
> the B1 preregistration's conservative static exemplar-supply bound (the twenty longest values of the
> frozen snapshot, 6,543 chars / 1,636 chars-over-4 proxy tokens, measured by the envelope render;
> receipt `coordination/slurp-b1-exemplars-k20-anchor-v2/exemplar-prompt-fit-v1.json`, SHA-256
> `fa2060af0621a920a590825749ec692cf9cbf75d1d41111965717742c79e10c6`), plus M4b's **largest** measured
> per-role-visit increment over the anchor anywhere, +965 tokens at `solver:1`.

**Cross-check:** the widest request realised on this base by any sealed cell is the twin's 16,869;
16,869 + 965 = **17,834**, below the registered bound. **Expected** widest high-count request:
15,976 + 384 = **16,360**. k = 12 is not needed and is not registered.

**The static bound is a pre-flight estimate; the FIT run is the authority.**
`core.preparation_fit.build_native_contact_fit_gate` fits every realized immutable request against the
resident tokenizer *before it is transmitted*, inside the same campaign and the same lease; a request
that would not fit stops the flight rather than being truncated. The verdict reports the realised
minimum margin and widest realised request against the bound above, and records any overshoot the way
B1's and B4b's verdicts recorded theirs.

Receipts cited in this section, by path under `SPEECHRL_DATA_DIR` and SHA-256:

| receipt | SHA-256 |
| --- | --- |
| `coordination/slurp-b5e-combination-v1/prompt-fit-v1.json` | `544903713390aad0a58986d528e71a9f100a87d63f25329230c11286198c0c5b` |
| `coordination/slurp-b1-exemplars-k20-anchor-v2/prompt-fit-v1.json` | `8b72aa67b9c0ebcf52379442f8e9dc0d62a2d8dfac91faae9af1618bd8632916` |
| `coordination/slurp-b1-exemplars-k20-anchor-v2/exemplar-prompt-fit-v1.json` | `fa2060af0621a920a590825749ec692cf9cbf75d1d41111965717742c79e10c6` |

## 10. Containment

`scripts/check_slurp_exemplar_containment.py` reproduces
`rails.runner._assert_agent_control_excludes_knowledge_payloads`'s exact rule (casefolded substring
test, 8-character protected-payload floor) over the 9,354 rendered `annotated-exemplars` values
against every composed instruction text this base sends. It was run on the anchor base for cell B1 and
returned **0 collisions** across all six composed texts
(`coordination/slurp-b1-exemplars-k20-anchor-v2/containment-v1.json`). **Cell B5e changes no
instruction text**: `phase_material`, `phase_tools`, `task_instruction_template`,
`task_instruction_fill` and every template path are composed byte-identical to the anchor's and to cell
B1's (section 4's composed-key table). The exemplar value pool is likewise unchanged — same release,
same snapshot, same 9,354 facets — so the B1 containment result carries over unchanged, and no
no-example task-contract projection is needed. **What M4b changes is the `slot-contracts` store's
content, not any instruction text**, and cell B4b flew that content on this base with the runtime rule
live and without a containment refusal.

## 11. Failure rule

Restated in full in section 7. The first failure stops the cell and preserves everything; at most one
root-diagnosed recovery re-registration; a second failure closes this flight and the fix must be proven
on a four-row dry run before another mechanism is admitted. A failed four-row smoke stops B5e until the
fix is proven on that same four-row roster.

## 12. What is NOT claimed

- **No superiority, generalization, paper-scale or held-out claim.** TRAIN Fold A is an exposed
  discovery roster. Nothing is said about Fold B, DEV-1000 or the test split, which stay unread.
- **Meeting the bar on this pass is not "replicated".** Owner decision 1's bar is "replicated on the
  same roster", and this is one pass. B5er is what replication means here.
- **No claim that the bar arithmetic predicts the result.** 62.67 + 2.06 = 64.73 is an extrapolation
  that this cell exists to test; sub-additivity is an expected outcome, not a defect.
- **No component-causal attribution below the two stores.** Eight cards moved together in the M4b
  release and twenty exemplars arrive together in M1; neither this cell nor its predecessors can say
  which card, which sentence or which exemplar paid.
- **No new claim about either module's own effect size.** The B1 and B4b verdicts stand unchanged
  beside this one; this cell measures the combination, not a re-estimate of its parts.
- **Nothing about the review loop**, which is the anchor's here and is not ablated. Its own decision is
  `docs/results/2026-09-17-slurp-b0-review-off-verdict.md` plus the 2026-09-17 own-null re-decision.
- **M4b's provisional status is not discharged here.** Owner decision 13's replication branch is the
  B4b request-identical replicate; this cell is a combination read, and a positive `(B5e minus B1)`
  contrast is not a replication of B4b.
- **A structural smoke result is never a quality result.**
- **No tuning.** No k, tau, threshold, fuse policy, release or snapshot moves, and no third module
  joins.

## 13. Analysis recipe

`docs/readiness/2026-09-18-slurp-b5e-combination-v1/analysis-recipe-v1.json` pins the four sealed score
artifacts and the conditional fifth, the roster metadata, the shared estimators
(`analysis.null_calibration_cli.rows_for`, `analysis.null_calibration.pooled_f1`,
`analysis.paired.resampled_statistic`, `analysis.paired.paired_contrast`), the seed, the draws, the two
interval levels, the contrasts, the own-null margins, the STOP condition and the metric list.
`analysis.score_compare_cli` is deliberately not the runner: it hard-codes CI90 and DEV population
names.

## 14. Pre-contact evidence on file

All under `SPEECHRL_DATA_DIR/coordination/slurp-b5e-combination-v1/`, outside the repository so no
receipt can dirty the tree the scoring gate reads at finalize.

| receipt | SHA-256 | what it proves |
| --- | --- | --- |
| `prepared-supply-comparison-v1.json` | `9b6f8771aa4b92a95ac89a25c9eba8a4af5fea48766834de419698419645554d` | both prepared artifacts pinned; their Perception `output` byte-identical to the sealed anchor's, cell B1's and cell B4b's on 1,080 / 1,080 and 4 / 4 rows |
| `composed-hashes-v1.json` | `aff1f87819727b47836a7cc4a22097e86c9c5909ca9727290f585491af3a4734` | the composed and protocol hashes of both cells; the exact composed-key diffs against the anchor, cell B1 and cell B4b; the store-by-store equality proofs; and the method verification (the same `compose()` / `protocol_hash()` call reproduces the sealed anchor's `d1c61c09…` and `2527b527…`, cell B1's `114b7917…` / `c66d507d…` and cell B4b's `8d207b33…` / `567a87ad…`) |
| `prompt-fit-v1.json` | `544903713390aad0a58986d528e71a9f100a87d63f25329230c11286198c0c5b` | the per-role-visit maxima of all 21,678 sealed fit receipts on this base, the module increments, and the registered static bound with its cross-check |
| `prepare-supply-arm-v1.json`, `prepare-supply-smoke-v1.json` | see `plan-hashes-v1.txt` | the raw model-free `prepare-supply` receipts, `contact_class = model-free` |
| `plan-hashes-v1.txt` | see the file | the SHA-256 of this preregistration, of every document in the readiness directory and of the five config fragments |

**No `core.flight.cli check` receipt is on file, and that is deliberate.** `FlightRuntime.preflight`
asserts a clean study tree and reserves the attempt in the durable `AttemptStore`; a registration agent
that has not committed cannot run it without either failing on its own uncommitted files or writing an
attempt reservation it has no authority to make. The composed and protocol hashes above were therefore
computed directly through `core.config.compose` / `core.config.protocol_hash` — the same two functions
`check` itself uses — and the method was verified four ways against sealed, registered values. The
coordinator's re-pin cycle runs `check` for both cells on the clean registration commit and **asserts
the runtime-derived hashes equal the ones it has just written**; if they differ by one character, the
launch stops. The runbook records the command.
