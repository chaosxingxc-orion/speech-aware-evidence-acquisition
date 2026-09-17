# Cell B1 on the sealed anchor base: speech-keyed exemplar supply to the Solver, preregistration

Status: **PREREGISTERED BEFORE CONTACT.** Author: the B1 re-base agent, worktree
`/home/chao/saea-worktrees/fable-b1-anchor-prep`, branch `fable/b1-anchor-prep`, base commit
`bd04f4b9`. Authority: `docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md` section 3
(module M1) and section 4 (Phase B, cell B1); the A2 decision
`docs/results/2026-09-17-slurp-a2-exemplar-headroom-audit-v1.md`; and owner decisions 6, 7 and 8 of
2026-09-17 (`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`). This document grants
no model contact; all three cells stay readiness `held` until the coordinator pins the root decision
receipt and flips them with `scripts/flights/repin_cell.py`.

Everything recorded here was produced with **zero model, tokenizer, encoder, ASR, scorer and server
contacts**. The resident service was never started, stopped or queried.

## 0. Why this package exists: the base moved

The v1 registration of this cell
(`docs/readiness/2026-09-17-slurp-b1-exemplars-k20-v1-preregistration.md`) was built on the
**review-off base** of cell B0 and carried the instruction, visible in its own section 2, that *"if
cell B0 lands HARMFUL, the coordinator re-bases both cells on the sealed anchor before launch"*.

Cell B0's first-pass verdict was HARMFUL by a width failure
(`docs/results/2026-09-17-slurp-b0-review-off-verdict.md`), and owner decision 6 of 2026-09-17
ordered a re-decision of module M0 under the TRAIN A **own null** measured by the byte-identical
replicate B0r. That read is now on file
(`SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-B0-REPLICATE-PAIRED-ANALYSIS-V1/README.md`;
`score-contrasts.json` SHA-256
`69abec23e2c6aecca0d55474268ae2c9966631f243497f354a95b332c7ceb849`) and returns **HARMFUL** again:
the intent clause fails on both passes, and the SLU clause fails once by 0.028 pp. Under the
preregistered consequence the Reviewer/Planner loop **stays**, and every later cell of the program
builds on the sealed dual-store anchor.

So this package re-registers cell B1 on the anchor with fresh v2 identities. The v1 package is
**superseded before contact**: it was never flown, its six exposure rows keep `consumed = no`, each
carries a supersession note, and none of its run or attempt ids may ever be reused.

The one substantive engineering change since the v1 registration is that its blocking gate is gone:
commit `d8d8844b` (merge `29bca551`, item E3b) narrowed
`rails.knowledge_stores.build_knowledge_store_supply` so a candidate supply and a *different* store's
later-phase plain `phase_supply` may share one phase. `check`, `prepare-supply`, the smoke and the
campaign all construct now, and the three E3 fragments' `"root": "repo"` defect is likewise repaired
on master.

## 1. Question

Do speech-keyed annotated TRAIN exemplars, supplied to the Solver as typed content blocks, improve
official pooled SLU-F1 over the **sealed dual-store anchor** on TRAIN Fold A 1,080?

A2 settled the availability side and nothing more: at plain k = 20 the twenty neighbours carry the
gold intent on 0.956 of rows, lift union coverage from the sealed 0.8676 to 0.9722, reach type
recall 0.960 and filler recall 0.566, and show no memorisation channel (exact-text-neighbour rate
0.0019). A2 also recorded the open question this cell answers: *union coverage is availability, not
use* — whether the Solver actually escapes to a neighbour intent is a B1 outcome.

## 2. Arms and comparators

| role | identity |
| --- | --- |
| treatment | `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-V2` / `attempt-slurp-native-exemplars-k20-anchor-train-fold-a-generation-v2`, cell `slurp-native-exemplars-k20-anchor-train-fold-a-v2`, composed config `c5bbdc2e1273a8de76b602b450f2da8c1c9092b703208739353b0b09e02fb67f`, protocol `b251f59a41a4e7cbcf6aae328c07148c4dda2dd0c557fd9576e2f26b10ab49f6` |
| twin | `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TWIN-TRAIN-FOLD-A-V2` / `attempt-slurp-native-exemplars-k20-anchor-twin-train-fold-a-generation-v2`, cell `slurp-native-exemplars-k20-anchor-twin-train-fold-a-v2`, composed config `25daa5afb334a899091c6481a9febb33660743bfe96286c8d89903339b788d5c`, protocol `4abd62bb6da4888095b57c843e59bb045a74bfb6fcce6b73ae3a4435f9207b2c` |
| smoke | `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-SMOKE-4-V2` / `attempt-slurp-native-exemplars-k20-anchor-smoke-4-generation-v2`, cell `slurp-native-exemplars-k20-anchor-smoke-4-v2`, composed config `cfaca2b20af9e08499769a232615d62f779e4777293b4089714fe28d464b7b00`, protocol `c31ac32fd609a2a17313b8fe9767528ccbeb1138ca24ecbcfa5b85cd811da335` |
| **primary comparator** | sealed bytes of `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1`, score artifact SHA-256 `7360876322488e5fda689fcafda00e90da2ebf559e5a35e635c550f940202b47`, run manifest `049ac230e536bc6c8fe45bc847756ba486c4904e9c7602c698157f78d70c0152`; official aggregate pooled SLU-F1 48.53, intent 77.96, scenario 84.81, action 79.26, pooled span F1 29.50 |
| **secondary comparator** | sealed bytes of the released TRAIN A direct anchor `SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-SOURCE-RECOVERY-V1`, score artifact SHA-256 `7840a959fe4f43928fda0e0cacfe8c0ee4200116bfcd269bfe3451b59da29c38`, run manifest `546109055a373b358c43d36878c532b95784ee5d73d07f011c5fa3ea3d7ce11e`; official aggregate pooled SLU-F1 33.89, intent 73.70, scenario 82.69, action 75.09, pooled span F1 21.10 |

Neither comparator is ever re-flown or re-scored. All arms share the roster
`docs/receipts/rosters/slurp-evo-fold-a-v2.json` (SHA-256
`1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d`), split `SLURP-EVO-FOLD-A-V2`,
split identity `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, role `discovery`,
and the resident session `serving-slurp-native-candidate-five-train-a-np4-v1` (attach only).

## 3. The one factor, and what it is not

Moved against the sealed anchor's own committed baseline
(`configs/baseline/slurp-native-dual-store-train-fold-a-anchor-recovery-v1.json`):
`knowledge_stores` gains **one** named store, `train-exemplars`, taken verbatim from the E3
deliverable `configs/baseline/slurp-native-dual-store-train-fold-a-exemplars-k20-v1.json`. Its Solver
block is plain top-k with k = 20, `saea-fuse-supplyfilter-v1` at m = c = top_l = 20,
`saea-rank-wcos-prior-agree-v1` with w_cos = 1 and w_prior = w_agree = 0, tau 0.0, keyed by the row's
own sealed Fold A full-utterance speech vector in the `content` dimension. The store's release and
snapshot are pinned (`171aa4a8…` / `4c498dc0…`) over a 9,354-facet pool that excludes every utterance
with a recording in TRAIN Fold A, Fold B or DEV-1000. Alongside it move only bookkeeping: this cell's
own `native_contact_fit` run and attempt ids at the unchanged eleven-contact ceiling, the two
speech-feature identity ids (provenance only), the exemplar store's own
`preparation_source_receipts` row (`"root": "repository"`), its own `prepared_phase_supply` pin, and
two free-English note blocks.

Held identical: the anchor role graph (perception 1, solver 1, **reviewer 3, planner 1,
max_revisions 1**, policy `phase-native-candidates-review-revise-v1`, program ceiling 11 contacts per
row), the roster and split, the model fragment and resident geometry, the promoted speech packets,
the `intent-boundaries` and `slot-contracts` stores with their release and snapshot hashes and the
four-candidate K8 / max 3 / 16 per candidate / 28 total supply contract, **every instruction
template** — the exemplars reach the model as typed content blocks on the acquire transition, never
as instruction text — the `phase_tools` Reviewer task-contract authority block, and the scorers.

The prepared first-phase Perception supply does not move either: `prepare-supply` was re-run
model-free at 8 workers for all three cells on this commit, and each artifact's Perception `output`
is **byte-identical to the sealed anchor's own** — `output_sha256`
`ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` on 1,080 of 1,080 rows for the arm
and the twin, and `512583ec2c684a2e285bfafea3f4101033a2a1d413fad39c8cfd2b74fbff5733` on 4 of 4 rows
for the smoke. Receipt: `coordination/slurp-b1-exemplars-k20-anchor-v2/prepared-supply-and-hashes-v1.json`.

### What the request actually looks like

Measured, not asserted, on every roster row through
`core.flight.runtime.render_phase_prompt_envelopes` — the one authority the pinned prompt-fit
measurement and its verification both use — against the sealed anchor's own committed fragments
(`coordination/slurp-b1-exemplars-k20-anchor-v2/request-envelope-comparison-v1.json`):

| phase | arm versus anchor | after removing the `train-exemplars` blocks |
| --- | --- | --- |
| perception | byte-identical on 1,080 / 1,080 | 1,080 / 1,080 |
| reviewer | byte-identical on 1,080 / 1,080 | 1,080 / 1,080 |
| planner | byte-identical on 1,080 / 1,080 | 1,080 / 1,080 |
| solver | differs on 1,080 / 1,080, by exactly 20 blocks per row | **1,080 / 1,080 identical** |

The same holds on the smoke roster (4 / 4). Neither the run id, the attempt id, nor either
speech-feature identity id appears in any rendered request byte, on any phase, for any arm.

One honest limit. `render_phase_prompt_envelopes` accumulates a phase's supply bound in
**declaration** order (`perception, reviewer, planner, solver`), so this static render shows the
exemplar blocks only at the Solver. At dispatch the native role episode executes
`perception -> solver -> reviewer -> planner`, and the supplied values stay visible in the
accumulated `QueryState`, so the Reviewer and Planner requests that follow a Solver contact carry the
same blocks. That runtime propagation is **stated here, not measured** by the static renderer; the
`native_contact_fit` gate fits every realized request immediately before dispatch and is the exact
per-request authority. The same asymmetry means the pre-flight prompt-budget estimate under-counts
those later Reviewer/Planner requests by at most one exemplar block; section 9 shows the resulting
worst case still clears the slot by more than 8,000 tokens.

## 4. The twin

Every row receives another Fold A recording's sealed full-utterance speech vector, drawn by a seeded
within-delivered-scenario derangement (`scripts/build_slurp_exemplar_twin_vectors.py`, seed
20260917; vectors `vectors/slurp-exemplars-twin/query-vectors-speech-segments-deranged-v1.jsonl`,
SHA-256 `92e7f72e5566aa8dad2ed75b8ddc3df58dd107ef2de57dc0e1aab66e2ad616c5`). Buckets come from the
sealed anchor's **delivered** scenario, never gold. The E3 derangement proof
(`coordination/slurp-b1-exemplars-k20-v1/twin-derangement-proof-v1.json`, recomputed from the two
sealed vector files alone) records 1,080 rows, ids identical and in the same order as the parent
file, **0 fixed points**, and — recorded rather than glossed — that it is *not* a strict bijection:
exactly one source vector is delivered to two rows and one to none, the arithmetic consequence of the
provenance's declared `cross_group_rows: 1`.

Because store, k, fuse policy, rendering and contact count are identical, the twin's exemplar block is
token-matched to the arm's by construction, and `arm minus twin` isolates the retrieval key.

**The twin flies only after the arm shows a positive CI95 against the base** (owner decision 8 of
2026-09-17). One cell in flight at a time.

## 5. Metrics

Primary: **official pooled SLU micro F1** from `slurp-slu-official-train` (pinned official
`evaluate.py`, `slurp-official-8eb16545`), natural mixture, one complete score per manifest through
`core.scoring_batch`, never sharded.

Secondaries: intent (joint scenario+action) accuracy, scenario accuracy, action accuracy, official
pooled span F1. Reported beside them: per-row mean official SLU-F1 and per-row mean exact slot F1,
saves/harms/ties with the exact two-sided McNemar p.

Diagnostics, mandatory in the verdict and never gates:

- **candidate-union coverage realized in the delivered answer**, against A2's availability number
  0.9722 — the direct answer to A2's own open question;
- **Solver escape-to-neighbour-intent rate**: the share of rows whose delivered intent is absent from
  the sealed Perception candidates but present among the supplied exemplar intents;
- **exemplar token volume actually rendered per row**, against the 1,083-token measured maximum;
- **revision counts and review-loop dispositions**, against the anchor's own five executed revisions
  and two intent changes in 1,080 rows — the loop is part of this base and its behaviour under
  exemplar supply is a reportable fact.

`delta = arm minus comparator`, in percentage points; negative means the arm is worse.

**Projection v3 beside every official number.** Owner decision 7 of 2026-09-17 makes
`slurp-slu-official-projected-v3-train` the fixed post-processing of every official number. Every
table in the verdict reports the v3 number beside the unprojected official number and beside the
symmetric-normalised view where one exists, and states that about 2.5 pp of the 64-point program bar
is representation alignment rather than capability. **The decision rule below reads the unprojected
numbers**, as registered; v3 never moves a verdict.

## 6. Resampling and tables

Paired whole-speaker cluster bootstrap, **10,000 draws, seed 20260915**, CI95 for advancement and
CI90 for diagnostics, both as percentile pairs of the same retained replicate sequence. Sensitivity:
paired scenario-stratified row bootstrap, same draws and seed. Every verdict carries the
per-scenario table in both the natural-mixture and the equal-scenario weighting; the equal-scenario
delta is reported beside the natural-mixture point estimate and never replaces it. Speaker clusters
come from the released roster metadata (125 speakers, 18 scenarios of 60 rows, 523 headset and 557
far-field rows).

## 7. Decision rule (fixed here, copied from the spec)

Null half-widths are the **TRAIN A own null** measured by cell B0r on this exact roster — the CI95
half-widths of (B0r minus B0): **SLU micro 1.1218, intent 1.0051**, scenario 1.0655, action 1.0327,
pooled span F1 1.5586 percentage points. They replace the imported DEV-1000 margins (intent 0.92, SLU
micro 1.18), which the 2026-09-08 family rule and the B0 re-decision both showed do not transfer to
this roster; the imported values gate nothing here.

- **ADMITTED** if the CI95 lower bound of the pooled SLU delta is greater than 0 **versus the sealed
  anchor AND versus the twin**, intent is non-inferior within h_intent = 1.0051 pp, the normalised
  scorer agrees in sign **where a TRAIN sibling exists**, and no scenario loses intent beyond the
  null band.
- **NEUTRAL** otherwise; it enters the default plan only if it lowers cost.
- **HARMFUL** otherwise, when a guard fails on the losing side.

**The normalised-scorer clause has no TRAIN sibling today.** `slurp-slu-f1-normalized-v1` is bound to
the `devel` split and refuses TRAIN sample ids — the B0r read hit exactly that refusal
(`SlurpOfficialEvalError: outputs sample_id 'slurp:train:000007:audio--1504197557' is not part of
SLURP split 'devel'`). The clause is therefore recorded as **not evaluable on this roster** and
reported as such in the verdict; it is not silently dropped, and it is not replaced by a substitute
scorer invented after the fact.

No repeat-to-pass: the verdict is read once, from the single official score of each complete
manifest. Scenario and action margins are diagnostics for the per-scenario table, not gates.

## 8. Cost

Registered ceilings per full cell, which are bounds and not targets: **11,880 generation contacts,
47,520 FIT endpoints, 33,930 repeated speech seconds, 12.0 fit-inclusive GPU hours, 6,480 native
task-contract calls, one official complete scoring job, zero ASR, encoder and paid-API calls.** The
generation ceiling is the exact program maximum on this role graph:
`1 + (max_revisions + 1) * (reviewer 3 + planner 1 + solver 1) = 1 + 2 * 5 = 11` contacts per row,
resolved by `rails.native_episode_config.load_native_episode_config` and verified on the composed
fragments, times 1,080 rows. The FIT ceiling is `1,080 * 11 * (1 speech packet + 3 endpoints)`. They
mirror the sealed anchor's own registration (`docs/readiness/2026-09-14-slurp-native-dual-store-train-fold-a-anchor-v1/`).

**Expected** spend is far below those bounds: the anchor realized 5,417 contacts (5.016 per row),
15,459.76 repeated speech seconds and 3.388 GPU hours on this geometry, and the exemplar block adds
prompt tokens, not contacts. Budget about **3.4 GPU hours per full cell**.

Smoke ceilings: 44 generation contacts, 176 FIT endpoints, 117 repeated speech seconds, 1.0
fit-inclusive GPU hours, 24 native task-contract calls, zero scoring jobs.

Mandatory in the verdict, per arm: actual generation contacts and contacts per row; actual repeated
speech seconds; actual FIT endpoints and minimum fit margin; GPU hours read from the serving monitor
(`SPEECHRL_DATA_DIR/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl`) over
each lease window, never a wall-clock guess; mean latency, slot occupancy, utilisation and parked
fraction from the same monitor; exemplar token volume actually rendered; preprocess and scoring wall
time.

## 9. Prompt fit

The 24,576-token serving slot. Measured base, recomputed here from the anchor's own **5,417 sealed
native contact-fit receipts** (`coordination/slurp-b1-exemplars-k20-anchor-v2/prompt-fit-v1.json`);
every one of them fits:

| role visit | contacts | max required tokens | min margin |
| --- | ---: | ---: | ---: |
| perception:0 | 1,080 | 4,270 | 20,306 |
| solver:0 | 1,080 | 13,157 | 11,419 |
| solver:1 | 5 | 13,482 | 11,094 |
| reviewer:0 | 1,080 | 13,259 | 11,317 |
| reviewer:1 | 1,077 | 15,037 | 9,539 |
| reviewer:2 | 5 | 13,596 | 10,980 |
| **reviewer:3** | 5 | **15,374** | 9,202 |
| planner:0 | 1,080 | 15,028 | 9,548 |
| **planner:1** | 5 | **15,382** | 9,194 |

The Reviewer and Planner requests are the anchor's largest — not the Solver's — because they carry
the Solver's draft and the accumulated state. The widest request of any role visit is `planner:1` at
15,382 tokens; the widest Reviewer visit is `reviewer:3` at 15,374.

The exemplar block, recomputed over the real sealed snapshot and the real sealed vectors and
cross-checked byte-for-byte against the real `KbFacetProvider`/rank/fuse pipeline on 5 random rows at
both k values (`coordination/slurp-b1-exemplars-k20-anchor-v2/exemplar-prompt-fit-v1.json`): at
k = 20, mean 2,974.4 chars, p50 2,907, p95 3,796, **max 4,332** — a chars/4 proxy of mean 743.6,
p95 949.0, **max 1,083.0** tokens. At the k = 12 fallback, max 2,730 chars / 682.5 proxy tokens.

**Upper bound for any B1 request: 15,382 + 1,083 = 16,465 required tokens, a margin of at least
8,111 against the slot.** The two maxima are taken over different rows and different role visits, so
the sum is a strict upper bound and not a realized worst case. Against the *conservative static
supply bound* the pre-flight budget uses (the twenty longest values of the frozen snapshot, 6,543
chars / 1,636 proxy tokens, measured by the envelope render) the bound is 17,018 tokens, margin
7,558. k = 12 is not needed. The runtime `check` receipt, which is the authority for the pre-flight
budget decision, is recorded in the runbook.

## 10. Containment

`scripts/check_slurp_exemplar_containment.py` reproduces
`rails.runner._assert_agent_control_excludes_knowledge_payloads`'s exact rule (casefolded substring
test, 8-character protected-payload floor) over the 9,354 rendered `annotated-exemplars` values
against the composed instruction text of every phase this base sends. Re-run on this commit for the
anchor base, **0 collisions** across all six composed texts: context 8,118 chars, perception 960,
planner 193, reviewer 435, solver 1,129, and the Perception `fill_params.source_catalog` 35,011. The
Reviewer and Planner templates — the two the review-off base never exercised — are explicitly among
them. No no-example task-contract projection is needed. Receipt:
`coordination/slurp-b1-exemplars-k20-anchor-v2/containment-v1.json`.

## 11. Failure rule

The first failure stops the cell and preserves everything. No automatic restart, replay, row
filtering, roster, role-graph, prompt, geometry or cap change, and no silent recovery. At most one
root-diagnosed recovery re-registration per run; a second failure closes that flight and the fix must
be proven on a four-row dry run before another mechanism is admitted. A failed four-row smoke stops
B1 until the fix is proven on that same four-row roster.

## 12. What is NOT claimed

- No superiority, generalization, paper-scale or held-out claim. TRAIN Fold A is an exposed discovery
  roster.
- No component-causal attribution beyond the one added store. An admitted result says exemplars
  supplied this way pay for themselves in this configuration, not that exemplar grounding is
  generally good.
- A2's availability numbers are not predictions of the delivered answer. Union coverage 0.9722 is
  what is *available*; B1 measures what is *used*.
- Nothing about Fold B, DEV-1000 or the test split; they stay unread.
- The twin is a token-matched retrieval-key control, not an information-free control: twenty real
  annotated exemplars still reach the Solver in the twin arm.
- A structural smoke result is never a quality result.
- Nothing here re-opens module M0. The review loop's retention is the B0 re-decision's outcome, not
  this cell's finding, and this cell measures no ablation of it.

## 13. Analysis recipe

`docs/readiness/2026-09-17-slurp-b1-exemplars-k20-anchor-v2/analysis-recipe-v1.json` pins the four
score artifacts, the roster metadata
(`analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/roster-metadata.json`, SHA-256
`07f4cd83b83d83d65500a328e0a38421ede575195c63ae118def0d1006c14e34`), the shared estimators
(`analysis.null_calibration_cli.rows_for`, `analysis.null_calibration.pooled_f1`,
`analysis.paired.resampled_statistic`, `analysis.paired.paired_contrast`), the seed, the draws, the
two interval levels, the four contrasts, the own-null margins and the metric list.
`analysis.score_compare_cli` is deliberately not the runner because it hard-codes CI90 and DEV
population names.

## 14. Pre-contact evidence on file

All under `SPEECHRL_DATA_DIR/coordination/slurp-b1-exemplars-k20-anchor-v2/`, outside the repository
so no receipt can dirty the tree the scoring gate reads.

| receipt | what it proves |
| --- | --- |
| `prepared-supply-and-hashes-v1.json` | the three prepared artifacts, their Perception `output` identical to the anchor's on every row, the composed and protocol hashes, the eleven-contact program ceiling, and the anchor method check (the same command on the anchor fragments returns the sealed anchor's registered protocol hash `2527b527…`) |
| `request-envelope-comparison-v1.json` | the row-by-row, phase-by-phase envelope comparison against the sealed anchor, including the stripped-block equality and the provenance-leak probe |
| `request-envelope-digests-v1.json` | the per-row per-phase envelope digests for all four arms |
| `prompt-fit-v1.json` | the anchor's per-role-visit sealed fit maxima over 5,417 receipts and the resulting upper bounds |
| `exemplar-prompt-fit-v1.json` (+ `.log`) | the k = 20 and k = 12 exemplar block size distributions, provider-verified on 5 rows per k |
| `containment-v1.json` (+ `.log`) | 0 collisions between the 9,354 rendered exemplar values and every composed instruction text |
| `ledger-parse-v1.json` | `contracts._parse_ledger_tables` sees all six new rows exactly once at `consumed = no`, and all six superseded v1 rows annotated and still `consumed = no` |
| `plan-hashes-v1.txt` | the SHA-256 of every document in the readiness directory |
| `check-*.json` | the runtime `check` receipts, recorded after the registration commit (runbook section 8) |

`core.flight.cli wire-check` is unavailable for any native-episode cell, as it was for the anchor,
B0 and B0r: `FlightRuntime._dispatch_phase_program` refuses a native episode whose transport is not
the real shared speech renderer, and `wire_check` installs a text transport double. The
request-envelope comparison of section 3 stands in its place.
