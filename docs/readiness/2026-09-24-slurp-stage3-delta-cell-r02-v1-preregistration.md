# Cell CELL-2: the locked v2.0 plan plus ITERATION 2 of the stage3-deltas store: preregistration

Registered 2026-09-24 by the CELL-2 registration agent (worktree `/home/chao/saea-worktrees/fable-cell2reg`,
branch `fable/cell2reg`) at base master `4c2e09c9`, per
`docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md` section S3-6 and owner decisions
83, 99, 101 and 106. Before any contact. **READINESS HELD**: this registration authorises no flight, no
readiness flip, no decision receipt, no exposure-row countersignature and no contact (section 9).

## 1. Why this cell exists

Cell CELL-1 flew the locked v2.0 plan plus the 379-value `stage3-deltas-v1r` store on TRAIN Fold A and read
**NEUTRAL by width, non-inferiority not proven**: official pooled SLU-F1 63.1502 against the sealed PLAN
arm's 63.6304 (-0.48 pp, CI95 [-2.18, +1.24]) and intent 81.4815 against 82.2222 (-0.74 pp, CI95 [-2.17,
+0.57]), with the derangement twin reproducing the arm within noise (-0.44 / +0.09) and the arm sitting off
both the prefilled-token and the GPU-hour frontier (+911.6 tokens per row, +2.5 % GPU-h). Owner decision 83
does not ask for the store to be thrown away on that reading; it asks for it to be **pruned by the
per-scenario effect, with the frontier slope as the cost weight**. That retention is done
(`docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1/iteration-2-retention-v1.md`): **200 values kept,
179 retired**. CELL-2 asks the only question the retention leaves open -- whether the pruned store buys
anything the unpruned one did not.

## 2. The factor and the arms

| item | value |
| --- | --- |
| base | the locked v2.0 plan, `configs/baseline/slurp-native-default-plan-lock-baseline-v1.json`, exactly as the sealed PLAN arm flew it (official 63.6304 / 82.2222) |
| factor | `knowledge_stores.stage3-deltas` and nothing else, at **version 2**: Perception **unconditional** cap 4 (`stage3-delta-unconditional-v1`), Solver cap 8, Reviewer cap 4, Planner cap 4 (`stage3-delta-candidate-bound-v1`, each bound to the row's own Perception candidate intents); every route `node_target`-filtered and `prior_score`-ranked. Identical to CELL-1's routing: **only WHICH rows the store carries moves** |
| store | `knowledge/slurp/semantic/stage3-deltas-v2/` -- release file `b81df5c5...`, snapshot content hash `44a80418...`; **200 values** (perception 80 / solver 76 / reviewer 40 / planner 4), 26 distinct facets, 219 facet entries (182 rows carry one, 17 carry two, 1 carries three), 136 source sample ids, statements 16,743 characters in total, mean 83.7 and longest 126, authored token count 3,001 |
| twin | `knowledge/slurp/semantic/stage3-deltas-twin-v2/` -- release file `b18b141f...`, snapshot content hash `13180912...`; the same 200 statements, the same node distribution, the same token count (3,001) and the same per-row facet-count multiset, attachment deranged as whole tuples under seed 20260922; **13 of 200** rows land on an equal facet set by arithmetic (26 intents over 200 rows) and are reported, not refused |
| retention | owner decision 83 as preregistered: retire when every targeted scenario is harmed beyond its own band, keep when any gains beyond it, otherwise the frontier-slope tie rule (keep only if the value's own per-delta paired SLU mean over the rows it reached exceeds 0.0 pp). 201 of 379 decided by the scenario rule (83 kept), 178 by the tie rule (117 kept). The band is **DERIVED** from one replicate pass -- `max(|PLANr - PLAN per-scenario delta|, 1.2485 pp)` -- and is a pruning rule, never a measured per-scenario null |
| population | TRAIN Fold A, 1,080 rows, split identity `61b0f062...5398b6`; the smokes read the same first four rows CELL-1's smokes flew, split identity `4e3413fe...b969cb` |
| comparator | the sealed PLAN arm `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1`, attempt `attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1`, **never re-flown** |
| predecessor | cell CELL-1 (`SAEA-SLURP-STAGE3-DELTA-CELL-R01-V1`), reported beside the verdict, **never a comparator** |
| margins | the plan's own null (PLAN vs PLANr): **h_SLU 1.2485, h_intent 0.9943** |
| contacts per row | ceiling **11**, the locked plan's own program maximum; the store adds supplied text to requests the plan already makes and adds no contact |
| session | `serving-slurp-native-candidate-five-train-a-np4-v1` (resident; attach only, never spawn or stop) |
| Stage-3 algorithm (decision 101) | `tfgrpo-semantic-advantage-v1`, operators `update` + `context_application`, iteration 2 |
| runs | arm `SAEA-SLURP-STAGE3-DELTA-CELL-R02-V1` / `-R02-FIT-V1`; twin `-R02-TWIN-V1` / `-R02-TWIN-FIT-V1`; smokes `-R02-SMOKE-4-V1` / `-R02-SMOKE-4-FIT-V1` and `-R02-SMOKE-4-TWIN-V1` / `-R02-SMOKE-4-TWIN-FIT-V1` |

**Why new identities.** CELL-1's run, attempt and fit identities are consumed; a `(run_id, attempt_id)` pair
is a one-time key, a plan budget is run-cumulative across every attempt of one run id, and the runbook's
`repoint` step -- which rewrites store pins in place -- is for a HELD cell, never for re-pointing a sealed
identity onto new content. CELL-2 is therefore a sibling fragment set, not an edit of CELL-1's six files,
and CELL-1's fragments are untouched by this registration.

## 3. Decision rule (fixed here, owner decision 99: the TRAIN lock)

Delta = CELL-2 minus the sealed PLAN arm, in percentage points.

- **ADMITTED** -- the CI95 lower bound of the paired **official pooled SLU-F1** delta is **above zero** and
  the CI95 lower bound of the paired **intent** delta exceeds **-0.9943**. A gain is proven, not merely
  non-inferior.
- **NEUTRAL** -- both guards non-inferior (SLU lower bound above -1.2485, intent lower bound above -0.9943)
  without a proven SLU gain.
- **HARMFUL** -- a **measured** loss on either guard (owner decision 25, Method B: a CI95 upper bound below
  zero, or a point estimate beyond the margin). Width alone is NEUTRAL, never HARMFUL.
- **TWIN = attribution, never admission.** A gain the twin reproduces within the plan's own null is **form**
  -- the store's shape and token volume -- not content, and the verdict says so and claims no content
  effect. At version 2 the store is SHORTER (3,001 authored tokens against 5,740), so a form effect is a
  live alternative explanation for any movement and the twin is what separates them.
- **SECOND LOOK** -- see section 3a. CELL-2 is read on the rows that chose the retained set.
- **Per-scenario harm bound** (owner decision 17) and **frontier row** (owner decision 75) as for CELL-1,
  diagnostics beside the verdict, never gates.
- **Delta-consumption table** (item S3-4s) -- per node and per scenario, placed beside CELL-1's own table,
  with the **Planner route reported separately**, never pooled.
- **Replication** -- an ADMITTED result is replicated on the **same roster** and then on a **fresh** one
  before any DEV, Fold B or test read. No such read is authorised by this package.

The read is executed by script (owner decision 58): `scripts/flights/batch/cell2_read.sh arm|twin`, which
drives `scripts/analysis/plan_cell_read.py` with `--registered
docs/readiness/2026-09-24-slurp-stage3-delta-cell-r02-v1/registered-facts-v1.json` and `--h-slu 1.2485
--h-intent 0.9943`. The exact invocations are in `analysis-recipe-v1.json` under `driver`.

### 3a. This is a SECOND LOOK on the same rows, and the verdict says so

The retention rule was applied to **CELL-1's own per-scenario and per-delta read of TRAIN Fold A**. CELL-2
is then scored on **those same 1,080 rows**. The rows that chose which deltas to keep are the rows the
keeping is measured on, so:

- CELL-2's verdict is a **development number** under owner decisions 28 and 86, and is not an independent
  confirmation of anything;
- an ADMITTED CELL-2 does **not** authorise a claim: the **replicate on a fresh roster (TRAIN Fold B or
  DEV)** precedes any effectiveness claim, and that replicate needs its own registration;
- a NEUTRAL or HARMFUL CELL-2 **is** informative in one direction: if pruning the deltas the CELL-1 read
  called harmful does not move the number on the very rows that called them harmful, the per-scenario
  signal the retention rests on was noise, and that is worth stating plainly in the verdict.

## 4. Smoke acceptance (four rows, structural only)

Beyond the standard list (4 rows delivered, no tools array, every request fits, dispositions counted, one
normaliser receipt per row, the Perception request differing from the comparator's by exactly the added
block), the structural rule for CELL-2's smoke is **the realised per-node supplied counts equal the offline
dry run's**, row by row. It is NOT "every route serves": see 4a.

### 4a. The registered offline dry run, and why "every route serves" is the wrong rule here

`analysis.native_episode_dry_run` walked the registered CELL-2 smoke composition on the REAL released
version-2 stores, contact-free, on **all four rows** with the Perception candidate ids the flight itself
produced (read off the retired CELL-1 v2 smoke attempt's own trace), plus a REVISE revisit and a
duplicate-candidate row. Driver: `scripts/flights/batch/cell2_dry_run.py`. Delta items supplied per node,
with the same walk over CELL-1's v1r store as the control:

| row | arm v2 S / R / P | arm v1r S / R / P | twin v2 S / R / P | twin v1r S / R / P |
| --- | --- | --- | --- | --- |
| `slurp:train:000007:audio--1504197557` | 0 / 1 / 0 | 1 / 3 / 1 | 1 / 0 / 0 | 0 / 4 / 1 |
| `slurp:train:000009:audio-1497557594-headset` | 0 / 0 / 0 | 4 / 0 / 0 | 0 / 0 / 0 | 3 / 1 / 0 |
| `slurp:train:000015:audio-1488524781` | 0 / 1 / 0 | 0 / 2 / 1 | 1 / 0 / 0 | 0 / 3 / 0 |
| `slurp:train:000023:audio-1490956038` | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |

(S = Solver cap 8, R = Reviewer cap 4, P = Planner cap 4. The Perception unconditional slice is **seeded**
before the walk rather than supplied at a node boundary, so it is not in these columns; its four value ids
are unchanged by the retention, because all four of CELL-1's seeds are kept and retirement only removes
rows. The v1r columns reproduce the CELL-1 package's own recorded table exactly, which is what makes this
driver's numbers trustworthy.)

Every walk **completes the whole graph** (perception -> solver -> reviewer -> planner, delivery from the
Solver's sealed draft) on every row, arm and twin. The REVISE revisit visits Solver, Reviewer and Planner a
second time and **acquires nothing** the second time. The duplicate-candidate row (n=3, distinct=1 -- the
shape that aborted the CELL-1 arm after 304 metered contacts) walks, with 3 candidate projections receipted.

**The honest reading of the zeros.** On these four rows the Solver and Planner routes select nothing at
version 2, and the Reviewer route selects one value on two rows. That is **not** an inert store and **not**
a wiring defect:

- the model-free reach measurement says **200 of 200** values are reachable by a registered candidate
  intent on **every** node, arm and twin (release pins `supply_reach`);
- these four rows' candidate intents are `audio_volume_*`, `play_*` and `iot_hue_*`, and those are exactly
  the scenarios the retention pruned hardest: **iot kept 0 of 19**, **play 1 of 25**, **audio 1 of 3**;
- CELL-1's own consumption table shows all four routes serving on the 1,080-row roster (perception 1,080
  rows / 4,320 items, solver 937 / 6,386, reviewer 982 / 3,722, planner 641 / 807), and the retention's
  upper bound on the reduction is solver 56.3 %, reviewer 49.3 %, planner 33.1 % of those items.

**The smallest honest change, and the one this package takes:** no cap is widened, no population is
redrawn, no store is edited, no route is added. The **smoke's acceptance criterion** is amended instead --
its job is to prove the composition walks and that the realised per-node counts are the predicted ones, and
the "routes actually serve" evidence is taken where CELL-1 took it anyway, from the **arm's** own
delta-consumption table over 1,080 rows. A realised smoke count that does not match the table above is a
FORM defect and stops the arm; a zero that does match it is the registered expectation.

**The Planner slice is the risk this cell must report, not hide.** Four of the 14 Planner values survive,
over 4 distinct intents, and CELL-1 already measured that route at 0.594 of rows supplied, 1.259 items per
supplied row and never at cap. If the arm's delta-consumption table shows the Planner route serving zero
rows of 1,080, the verdict says the route was inert at version 2 and attributes whatever effect exists to
the other three routes. The arm's preflight carries the same inert-route check at population level (the
B9a-rec lesson).

## 5. Budgets

| quantity | arm | twin | each four-row smoke |
| --- | --- | --- | --- |
| rows | 1,080 | 1,080 | 4 |
| per-row ceiling | 11 | 11 | 11 |
| `planned_model_calls` / `generation_calls_cap` | **11,880** = 1,080 x 11 | 11,880 | **44** = 4 x 11 |
| `fit_endpoint_calls_cap` | **47,520** = 11,880 x (1 speech packet + 3 endpoints) | 47,520 | **176** |
| `planned_speech_audio_seconds` / `repeated_speech_audio_seconds_cap` | 33,930 | 33,930 | 117 |
| `planned_gpu_hours` / `gpu_hours_fit_inclusive` | 12.0 | 12.0 | 1.0 |
| `native_task_contract_calls_cap` | 6,480 | 6,480 | 24 |
| `official_complete_scoring_jobs` | 1 | 1 | 0 |

Every number is cell PLAN's and CELL-1's own registered ceiling, unchanged: this cell is the locked plan
plus one store, so its role graph and its per-row ceiling are PLAN's.

**Cost, registered before contact.** CELL-1 realised 4,553 contacts (4.216 per row), 9,264.9 prefilled
tokens per row and 1.8021 GPU hours per 1,080; the sealed PLAN arm realised 4,424 contacts (4.096 per row),
8,353.2 tokens per row and 1.7579 GPU-h. Version 2 supplies **fewer items at three of four nodes and adds
no contact**, and its worst-case supplied characters per node are 476 / 850 / 416 / 269 against v1r's 485 /
938 / 423 / 381. The registered expectation is therefore **no more than CELL-1's 9,264.9 prefilled tokens
per row and no more than its 1.8021 GPU hours per 1,080**, with the realised numbers measured, never
predicted -- and NOT a return to the PLAN row, because Perception's four unconditional items per row and the
binding Solver and Reviewer caps stay. Ceilings are bounds, never targets; budgets are run-cumulative across
every attempt of a run id.

**Fit.** `native_contact_fit`, fitted inside the same flight under the same lease. `coordinate-fit` must
**not** be run. Each cell carries its OWN fit identity (item E16), and a recovery re-registration needs
**both** a new generation attempt id **and** a new `native_contact_fit.attempt_id` in the baseline -- the
rule CELL-1 learned by losing two relaunches to a fit identity that already carried evidence.

**Prompt fit, measured on the committed tree** by `core.flight.cli check` (exit 0 on all eight cells):

| phase | decision | required window tokens | operational margin |
| --- | --- | --- | --- |
| perception | ALLOW | 19,992 | +1,512 |
| reviewer | ALLOW | 19,856 | +1,648 |
| planner | ALLOW | 19,795 | +1,709 |
| **solver** | **COMPACT_REQUIRED** | 21,821 | **-317** |

against the 24,576-token live slot less its one-eighth (3,072) reserve. The twin's bound is identical
and each smoke's is within one token (19,992 / 19,855 / 19,794 / 21,820). These are **identical to
CELL-1's to the token**, and deliberately so: the runtime's bound is the WORST CASE the supplied stores can render,
driven by the per-node caps and the longest statement (126 characters at both versions), neither of which
the retention moves. What version 2 lowers is the realised prefill, which the flight measures. The episode
declares `context_fit_policy` `compact-or-abstain`, so a Solver request that really exceeds the window is
compacted, never truncated, and every compaction is counted in the E20 receipts (CELL-1 compacted zero
rows).

## 6. Boundary

The store's `source_sample_ids` are **136 R01C construction utterances** (`source_split_identity_hash`
`7c603857...c46d7`), a subset of CELL-1's 223: retiring rows retires their sources. The release
registrations pin **TRAIN Fold A**, **TRAIN Fold B** and **DEV-1000** as `forbidden_rosters` and
`core.semantic_knowledge_preparation.prepare_semantic_knowledge_store` verified each by SHA-256 at release
time. No evaluated row of this cell's own population contributed a delta. No gold label, reference
transcript, delivered answer or future turn enters runtime. TRAIN Fold A is the roster the sealed PLAN arm
and CELL-1 already flew, so this cell opens **no new speech identity**. TRAIN Fold B, DEV-1000, DEV-2000,
DEV-2000-ADDED and the test split stay untouched and unread.

## 7. What is registered

Package `docs/readiness/2026-09-24-slurp-stage3-delta-cell-r02-v1/`:

| file | what |
| --- | --- |
| `README.md` | the engineering record: the release, the derivation from CELL-1, the dry run and the proofs |
| `protocol-registered-v1.json` | the registered protocol (factor, twin, store facts, iteration, population, decision rule, accounting, fit, prompt fit, boundary, smoke acceptance, derivation) |
| `registered-facts-v1.json` | the facts `scripts/analysis/plan_cell_read.py` reads against (`--registered`) |
| `analysis-recipe-v1.json` | the read: driver, stages, exact arm and twin invocations, tables, diagnostics |
| `generation-plan-registered-v1.json` | arm generation plan |
| `fit-plan-registered-v1.json` | arm native-contact-fit plan |
| `twin-generation-plan-registered-v1.json` | twin generation plan |
| `twin-fit-plan-registered-v1.json` | twin native-contact-fit plan |
| `smoke-generation-plan-registered-v1.json` | smoke generation plan |
| `smoke-fit-plan-registered-v1.json` | smoke native-contact-fit plan |
| `twin-smoke-generation-plan-registered-v1.json` | twin smoke generation plan |
| `twin-smoke-fit-plan-registered-v1.json` | twin smoke native-contact-fit plan |

plus the campaign plans `configs/campaign/slurp-native-stage3-delta-cell-r02-v1.json` and
`...-r02-twin-v1.json`, the six config fragments (four baselines and two experiment fragments), **eight**
unconsumed DRAFT exposure-ledger rows, and the runbooks
`scripts/flights/batch/cell2_repin_{smoke,twin_smoke,arm,twin}.sh`, `cell2_flip_all.sh`,
`batch_chain_cell2.sh`, `cell2_read.sh` and `cell2_dry_run.py`.

**The two v2 release registrations are REFERENCED, not copied**: `stage3-deltas-v2-release-registration.json`
(sha256 `9ad980f0...`) and `stage3-deltas-twin-v2-release-registration.json` (sha256 `548f6640...`) stay in
the CELL-1 package, where the release that produced them recorded them --
`core.semantic_knowledge_preparation` records a registration by its repo-relative path and the released
`release.json` binds exactly that path, so a copy would be a second file to keep true for no gain.

### 7a. How CELL-2 differs from CELL-1, and why

1. **Store pins** moved to `knowledge/slurp/semantic/stage3-deltas{,-twin}-v2/` in all four baselines;
   every other decided key is CELL-1's byte for byte, so the one-factor property against the locked plan
   holds by construction.
2. **Identities**: eight new run ids, four new attempt ids, four new fit identities. Nothing of CELL-1's is
   reused or rewritten.
3. **`prepared_phase_supply` is absent** from all four baselines (the cell-P0 form). The flip mints each
   cell's own artifact under its own run id (item E16) and inserts the matching `preparation` requirement;
   `--allow-output-change` must never be passed, and a CHANGED output means the knowledge channel moved.
4. **No decision requirement** is registered in either fragment: `repin_cell.py` inserts the real one at the
   flip, and a placeholder without an `expected_decision_id` would refuse the campaign at load.
5. **The two smoke FIT identities are declared as held cells**, where CELL-1 left them undeclared (cell
   PLAN's form). Each of this family's eight run ids therefore carries a cell, a registered plan document,
   an exposure row and its own `core.flight.cli check`. This is the only intentional shape difference and it
   authorises nothing extra: both stay held and are never flown as generation cells.
6. **The release was run step by step** (the runbook's steps B, C, W, D, E, R), because its step F re-points
   CELL-1's SEALED fragments; the fill stage was not run at all and CELL-1's fragments are untouched.

## 8. Registered hashes

| run id | cell | plan | composed config | protocol hash | split identity |
| --- | --- | --- | --- | --- | --- |
| `SAEA-SLURP-STAGE3-DELTA-CELL-R02-V1` | `...-r02-v1` | `generation-plan-registered-v1.json` | `4f69a5cd6742092512cd939fd4767f05e20735a7a495fe601a921747d49e1634` | `01cd0a24631f14812d6f567f45438fdbce6b25077b68b7b43c05246cbc2f89ea` | `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6` |
| `SAEA-SLURP-STAGE3-DELTA-CELL-R02-FIT-V1` | `...-r02-fit-v1` | `fit-plan-registered-v1.json` | same | same | same |
| `SAEA-SLURP-STAGE3-DELTA-CELL-R02-TWIN-V1` | `...-r02-twin-v1` | `twin-generation-plan-registered-v1.json` | `dfb5ccf3fa5d951ff20b11f4b6602f2ae48cdaa2df662783cf7d0c7810a16913` | `31d180fd00a4178a6e7b0137a83f992f84b2c4a562de54284cf2cf86b54553b3` | same |
| `SAEA-SLURP-STAGE3-DELTA-CELL-R02-TWIN-FIT-V1` | `...-r02-twin-fit-v1` | `twin-fit-plan-registered-v1.json` | same | same | same |
| `SAEA-SLURP-STAGE3-DELTA-CELL-R02-SMOKE-4-V1` | `...-r02-smoke-4-v1` | `smoke-generation-plan-registered-v1.json` | `58f6f9826b459e02672ed70e70e3560aa341b36c38f275985e35ea4d53e5ab98` | `5fae760da954ba3e5c70333b6edae71d35dde9230adf0038560943ffbd8caec0` | `4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb` |
| `SAEA-SLURP-STAGE3-DELTA-CELL-R02-SMOKE-4-FIT-V1` | `...-r02-smoke-4-fit-v1` | `smoke-fit-plan-registered-v1.json` | same | same | same |
| `SAEA-SLURP-STAGE3-DELTA-CELL-R02-SMOKE-4-TWIN-V1` | `...-r02-smoke-4-twin-v1` | `twin-smoke-generation-plan-registered-v1.json` | `c579a1fa78ea005967cd93d6660b92582b7de00f6838de26830fea32b6d3ea63` | `08047a47d37ce44ce8a93b81b1507df7648f6e16fcf07874c4efdc0d35ddce07` | same |
| `SAEA-SLURP-STAGE3-DELTA-CELL-R02-SMOKE-4-TWIN-FIT-V1` | `...-r02-smoke-4-twin-fit-v1` | `twin-smoke-fit-plan-registered-v1.json` | same | same | same |

Protocol document `protocol-registered-v1.json` sha256
`958d60941227ef299f4c8763bf9fe16536d50ff071704dfc143ccd0f0a78f3e6`.

`core.flight.cli check` exits **0 on all eight cells** on this committed tree, with `prepared_artifacts_ok:
true` (no pin yet: the flip mints each cell's own), `scientific_readiness.state` `held`,
`generation_authorized` false and **no blocker**. **Every one of these hashes moves at the readiness flip**
(the flip edits the readiness block, which `compose()` hashes), and `scripts/flights/repin_cell.py` --
driven by `repin_loop_generic.sh` -- rewrites the plans, this note, the README and the exposure rows in
dependency order.

## 9. What this registration does NOT authorise (readiness held)

`readiness.state` is `"held"` on all eight cells. No decision id is minted, no `scripts/flights/repin_cell.py
--set-ready` has run, no exposure row is countersigned (all eight read `consumed = no` and carry `REGISTERED
BEFORE CONTACT (draft, root countersignature pending)`), and no cell is on the batch queue. No model,
tokenizer, encoder, ASR, scorer, server, GPU, network or paid-API contact was made by this registration. The
only data-root write it made is the RELEASE of the two version-2 stores and their release-pins document,
which the coordinator authorised and which is reversible: an unflown store.

Also not authorised: any DEV, TRAIN Fold B or test read; the same-roster replicate; iteration 3 of the
store; any edit of a released store (version 1, 1r and 2 and their twins are read-only and pinned by
SHA-256 here); any re-flight or re-read of CELL-1; and any claim that Training-Free GRPO beats GEPA or ACE.

## 10. The coordinator's sequence

On the main checkout, after merging `fable/cell2reg`. Nothing below was performed by the registering agent.

**1. Mint the decision receipt** from the sealed CELL-1 receipt (WSL, from the study root):

```
python scripts/flights/batch/mint_decision_receipt.py \
  --from stage3-delta-cell-r01 --from-tag STAGE3-DELTA-CELL-R01 --from-date 2026-09-22 \
  --name stage3-delta-cell-r02 --tag STAGE3-DELTA-CELL-R02 --date 2026-09-24 \
  --expected-contacts 4553 --expected-gpu-hours 1.81 \
  --replace 'SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-TWIN-FIT-V1=SAEA-SLURP-STAGE3-DELTA-CELL-R02-SMOKE-4-TWIN-FIT-V1' \
  --replace 'SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-TWIN-V1=SAEA-SLURP-STAGE3-DELTA-CELL-R02-SMOKE-4-TWIN-V1' \
  --replace 'SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V3-FIT-V1=SAEA-SLURP-STAGE3-DELTA-CELL-R02-SMOKE-4-FIT-V1' \
  --replace 'SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V2-FIT-V1=SAEA-SLURP-STAGE3-DELTA-CELL-R02-SMOKE-4-FIT-V1' \
  --replace 'SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-FIT-V1=SAEA-SLURP-STAGE3-DELTA-CELL-R02-SMOKE-4-FIT-V1' \
  --replace 'SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V3=SAEA-SLURP-STAGE3-DELTA-CELL-R02-SMOKE-4-V1' \
  --replace 'SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V2=SAEA-SLURP-STAGE3-DELTA-CELL-R02-SMOKE-4-V1' \
  --replace 'SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V1=SAEA-SLURP-STAGE3-DELTA-CELL-R02-SMOKE-4-V1' \
  --replace 'SAEA-SLURP-STAGE3-DELTA-CELL-TWIN-FIT-V1=SAEA-SLURP-STAGE3-DELTA-CELL-R02-TWIN-FIT-V1' \
  --replace 'SAEA-SLURP-STAGE3-DELTA-CELL-TWIN-V1=SAEA-SLURP-STAGE3-DELTA-CELL-R02-TWIN-V1' \
  --replace 'SAEA-SLURP-STAGE3-DELTA-CELL-R01-FIT-V1=SAEA-SLURP-STAGE3-DELTA-CELL-R02-FIT-V1' \
  --replace 'SAEA-SLURP-STAGE3-DELTA-CELL-R01-V1=SAEA-SLURP-STAGE3-DELTA-CELL-R02-V1' \
  --replace 'slurp-native-stage3-delta-cell-smoke-4-twin-v1=slurp-native-stage3-delta-cell-r02-smoke-4-twin-v1' \
  --replace 'slurp-native-stage3-delta-cell-smoke-4-v3=slurp-native-stage3-delta-cell-r02-smoke-4-v1' \
  --replace 'slurp-native-stage3-delta-cell-smoke-4-v2=slurp-native-stage3-delta-cell-r02-smoke-4-v1' \
  --replace 'slurp-native-stage3-delta-cell-smoke-4-v1=slurp-native-stage3-delta-cell-r02-smoke-4-v1' \
  --replace 'slurp-native-stage3-delta-cell-twin-smoke-4-baseline-v1=slurp-native-stage3-delta-cell-r02-twin-smoke-4-baseline-v1' \
  --replace 'slurp-native-stage3-delta-cell-smoke-4-baseline-v1=slurp-native-stage3-delta-cell-r02-smoke-4-baseline-v1' \
  --replace 'slurp-native-stage3-delta-cell-twin-baseline-v1=slurp-native-stage3-delta-cell-r02-twin-baseline-v1' \
  --replace 'slurp-native-stage3-delta-cell-baseline-v1=slurp-native-stage3-delta-cell-r02-baseline-v1' \
  --replace 'knowledge/slurp/semantic/stage3-deltas-twin-v1r=knowledge/slurp/semantic/stage3-deltas-twin-v2' \
  --replace 'knowledge/slurp/semantic/stage3-deltas-v1r=knowledge/slurp/semantic/stage3-deltas-v2' \
  --replace '02505ba2e548a008cc6c16ffda6f7b9bff505061863026a3d7e1396c26d6c2e0=b81df5c5175e45e68933d4875c110fd46bea933283631d2c428187c480fc31f0' \
  --replace 'e2552666ebe6dcd87e4239bfddb3a02d62e8965280b9f52c40acf9cbf4b2f27d=44a804184cf83a08e85831d40bae942af1e71ed4365b485d833f9a03807ef150' \
  --replace '7c0dc8979e8b9f1ae66105049168b310d5136c99983f99a98885d01e27d84219=b18b141f67dae4b413391d22dd787a3b85480d2b4fab24db0848e547e7aa1a9a' \
  --replace '5aee8d1df90430272d7eedbafb2ab4fe032178a7b681b692b8234ecb2e56fb98=131809122d23ccdaac86c9a9426c5e045a9544fc3059c1b46f80a3365151d614' \
  --decision "<one sentence: what is admitted>" \
  --authority "<owner decisions 83 / 99 / 101 / 106; spec S3-6; the CELL-1 read and its decision-83 retention>" \
  --claim-boundary "<TRAIN development numbers; a SECOND look on the rows that chose the retained set; the twin decides attribution, never admission; no DEV, Fold B or test read>"
```

The `--replace` pairs are applied **in order**, after the tool's own five id substitutions (which already
rewrite `slurp-stage3-delta-cell-r01-admission-v1`, every `slurp-native-stage3-delta-cell-r01-` prefix, the
readiness directory and the coordination directory). The longer id always precedes the shorter one it
contains. **The two split identities need no substitution**: unlike the ADV-1 receipt CELL-1 minted from,
the CELL-1 receipt already names TRAIN Fold A (`61b0f062...`) and the four-row smoke split
(`4e3413fe...`), which are CELL-2's own. Check after minting that no `R01`, `-v1r`, `02505ba2`, `7c0dc897`,
`SMOKE-4-V1`, `SMOKE-4-V2` or `SMOKE-4-V3` substring survives.

**1b. Three fields the tool cannot set.** Before the flip, on the data root:

```
python - <<'PY'
import io, json
p = "$SPEECHRL_DATA_DIR/coordination/slurp-stage3-delta-cell-r02-v1/root-admission-v1.json"
d = json.load(io.open(p, encoding="utf-8"))
d["eligible_run_ids"] = [
    "SAEA-SLURP-STAGE3-DELTA-CELL-R02-SMOKE-4-V1", "SAEA-SLURP-STAGE3-DELTA-CELL-R02-SMOKE-4-FIT-V1",
    "SAEA-SLURP-STAGE3-DELTA-CELL-R02-SMOKE-4-TWIN-V1", "SAEA-SLURP-STAGE3-DELTA-CELL-R02-SMOKE-4-TWIN-FIT-V1",
    "SAEA-SLURP-STAGE3-DELTA-CELL-R02-V1", "SAEA-SLURP-STAGE3-DELTA-CELL-R02-FIT-V1",
    "SAEA-SLURP-STAGE3-DELTA-CELL-R02-TWIN-V1", "SAEA-SLURP-STAGE3-DELTA-CELL-R02-TWIN-FIT-V1"]
d["budget"]["arm"].update({"generation_calls_cap": 11880, "fit_endpoint_calls_cap": 47520,
                           "repeated_speech_audio_seconds_cap": 33930, "gpu_hours_fit_inclusive_cap": 12.0,
                           "native_task_contract_calls_cap": 6480, "official_complete_score_jobs": 1,
                           "ceiling_note": "11 contacts per row = 1 + 2 x (3 + 1 + 1), the locked plan's own"})
d["budget"]["smoke"].update({"generation_calls_cap": 44, "fit_endpoint_calls_cap": 176,
                             "repeated_speech_audio_seconds_cap": 117, "gpu_hours_fit_inclusive_cap": 1.0,
                             "native_task_contract_calls_cap": 24, "official_complete_score_jobs": 0})
d["registered_hashes"].update({
    "arm_composed_config": "4f69a5cd6742092512cd939fd4767f05e20735a7a495fe601a921747d49e1634",
    "arm_protocol": "01cd0a24631f14812d6f567f45438fdbce6b25077b68b7b43c05246cbc2f89ea",
    "smoke_composed_config": "58f6f9826b459e02672ed70e70e3560aa341b36c38f275985e35ea4d53e5ab98",
    "smoke_protocol": "5fae760da954ba3e5c70333b6edae71d35dde9230adf0038560943ffbd8caec0"})
d["cell_kind"] = ("Stage-3 S3-6 one-factor knowledge cell, ITERATION 2: the locked v2.0 plan plus the "
                  "retained 200-value stage3-deltas store, read against the sealed PLAN arm at the plan's "
                  "own null, with a derangement twin as the form control. A SECOND look on the TRAIN Fold A "
                  "rows whose CELL-1 read chose the retained set.")
io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=2) + "\n")
PY
```

Check after minting that `decision_id` is `slurp-stage3-delta-cell-r02-admission-v1`, that
`eligible_run_ids` names exactly the eight ids above, and that `population` still describes TRAIN Fold A
1,080 and the four-row smoke.

**2. Flip the four generation cells** -- smoke, twin smoke, arm, twin -- one cycle each, on the clean tree:

```
bash scripts/flights/batch/cell2_flip_all.sh
```

which drives `repin_loop_generic.sh` over `cell2_repin_smoke.sh`, `cell2_repin_twin_smoke.sh`,
`cell2_repin_arm.sh` and `cell2_repin_twin.sh`. Each pass re-pins with `scripts/flights/repin_cell.py
--set-ready`, commits, and re-runs until the freshly composed hashes and the registered documents agree. The
four FIT cells stay `held` -- they are spend identities, never flown as generation cells.

**3. Chain the flights** through the batch driver only (owner decision 77):

```
bash scripts/flights/batch/batch_chain_cell2.sh
```

Two steps: step 1 flies the generation smoke then the 1,080-row arm; step 2 flies the twin smoke then the
1,080-row twin. Expected rows 4 then 1,080 per step, `contacts_per_row` 4 (CELL-1 realised 4.216),
`ceiling_per_row` 11, tool-free, session `serving-slurp-native-candidate-five-train-a-np4-v1`. Each arm
opens only after its own smoke seals, and the twin never flies beside the arm. An aborted campaign leaves
`locks/flight.lock` behind; clear it before the next launch.

**4. Read**, arm first, then the twin: `bash scripts/flights/batch/cell2_read.sh arm|twin`, as
`analysis-recipe-v1.json` records. **5. Countersign** the eight exposure rows as the flights consume them.
Do not countersign before contact.
