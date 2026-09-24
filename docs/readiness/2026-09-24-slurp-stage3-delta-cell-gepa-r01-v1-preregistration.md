# Cell CELL-1-GEPA: the locked v2.0 plan plus the GEPA family's stage3-deltas store: preregistration

Registered 2026-09-24 by the CELL-1-GEPA registration agent (worktree
`/home/chao/saea-worktrees/fable-gepacell`, branch `fable/gepacell`) at base `fable/gepafix`
`9b0c4dd4`, per `docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md` section
S3-6, `docs/superpowers/specs/2026-09-24-slurp-stage3-gepa-arm-design.md`, the diff plan
`docs/readiness/2026-09-24-slurp-stage3-gepa-r01-v1/cell-1-gepa-diff-plan-v1.md` and owner decisions
83, 99, 101 and 106. Before any contact. **READINESS HELD**: this registration authorises no flight,
no readiness flip, no decision receipt, no exposure-row countersignature and no contact (section 9).

## 1. Why this cell exists

Owner decision 101 says the Stage-3 layer-A families -- Training-Free GRPO, GEPA, ACE -- fly on the
SAME ROLL-1 rollouts and the SAME locked plan, and are distinguished by an explicit, machine-checked
label. The diff plan makes that concrete: **the three families differ ONLY in the delta store they
release, so their arms are comparable by construction.** CELL-1 flew the Training-Free GRPO store
(`stage3-deltas-v1r`, 379 values) and read NEUTRAL by width -- SLU-F1 63.1502 against the sealed PLAN
arm's 63.6304 (-0.48 pp, CI95 [-2.18, +1.24]), intent 81.4815 against 82.2222 (-0.74 pp, CI95
[-2.17, +0.57]) -- with **large and opposite per-scenario effects** (audio +8.9, weather +8.3
against general -12.4, alarm -6.8). That pattern is what the GEPA arm exists to address: ADV-1
assigns credit per ROW, GEPA assigns credit per SCENARIO and mutates the guidance text.

The GEPA proposer cell `SAEA-SLURP-STAGE3-GEPA-R01-V1` has sealed, its store is released, and
CELL-1-GEPA is the cell that puts that store on the locked plan and reads it against the same
comparator, at the same own null, on the same rows.

## 2. The factor and the arms

| item | value |
| --- | --- |
| base | the locked v2.0 plan, `configs/baseline/slurp-native-default-plan-lock-baseline-v1.json`, exactly as the sealed PLAN arm flew it (official 63.6304 / 82.2222) |
| factor | `knowledge_stores.stage3-deltas` and nothing else: Perception **unconditional** cap 4 (`stage3-delta-unconditional-v1`), Solver cap 8, Reviewer cap 4, Planner cap 4 (`stage3-delta-candidate-bound-v1`, each bound to the row's own Perception candidate intents); every route `node_target`-filtered and `prior_score`-ranked. Identical to CELL-1's and CELL-2's routing: **only WHICH rows the store carries moves** |
| store | `knowledge/slurp/semantic/stage3-deltas-gepa-v1/` -- release file `53c12671...`, snapshot content hash `560d84e7...`; **448 values** (perception 142 / solver 137 / reviewer 92 / planner 77), 38 distinct facets, 780 facet entries (251 rows carry one, 98 two, 80 three, 3 four, 15 five, 1 six), 201 source sample ids, statements 39,839 characters in total, mean 88.9 and longest 140, authored token count 7,345 |
| store provenance | **248 GEPA-authored rows + 200 iteration-1 rows retained by the decision-83 rule.** The 248 come from the proposer cell's 68 reflective contacts, one per (scenario, node) group over the sealed ROLL-1 trajectories of R01C (17 scenarios x 4 nodes; `music` had no eligible row). The 200 are v1r's survivors under the retention over CELL-1's own read (200 kept of 379, 179 retired and held as dedup tombstones). Per node: GEPA-authored perception 62 / solver 61 / reviewer 52 / planner 73; retained perception 80 / solver 76 / reviewer 40 / planner 4 |
| twin | `knowledge/slurp/semantic/stage3-deltas-gepa-twin-v1/` -- release file `fb2dad30...`, snapshot content hash `f19671d3...`; the same 448 statements, the same node distribution, the same authored token count (7,345) and the same per-row facet-count multiset, attachment deranged as whole tuples under seed **20260924**; **16 of 448** rows land on an equal facet set by arithmetic (38 intents over 448 rows) and are reported, not refused |
| permitted roster | `docs/receipts/rosters/slurp-stage3-advantage-r01c-disagreeing-v1.json` (`SLURP-STAGE3-ADVANTAGE-R01C-DISAGREEING-V1`, 225 construction rows, split identity `7c603857...c46d7`) -- **the same receipt v1r and v2 pin**, so this store shares their source identity rather than inventing a third one. The 448 rows cite 201 distinct sample ids, all inside it; 28 of those ids are cited only by retained rows and lie outside the 173 GEPA group rows, which is why the group-rows roster is the record of what a contact was SHOWN and not the store's permitted roster (the GEPA package's own ruling of 2026-09-24) |
| population | TRAIN Fold A, 1,080 rows, split identity `61b0f062...5398b6`; the smokes read the same first four rows CELL-1's and CELL-2's smokes flew, split identity `4e3413fe...b969cb` |
| comparator | the sealed PLAN arm `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1`, attempt `attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1`, **never re-flown** |
| predecessor context | cell CELL-1 (`SAEA-SLURP-STAGE3-DELTA-CELL-R01-V1`), reported beside the verdict, **never a comparator** |
| margins | the plan's own null (PLAN vs PLANr): **h_SLU 1.2485, h_intent 0.9943** |
| contacts per row | ceiling **11**, the locked plan's own program maximum; the store adds supplied text to requests the plan already makes and adds no contact |
| session | `serving-slurp-native-candidate-five-train-a-np4-v1` (resident; attach only, never spawn or stop) |
| Stage-3 algorithm (decision 101) | `gepa-reflective-pareto-v1`, operators `update` + `selection` -- see section 2a |
| runs | arm `SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-V1` / `-GEPA-R01-FIT-V1`; twin `-GEPA-R01-TWIN-V1` / `-GEPA-R01-TWIN-FIT-V1`; smokes `-GEPA-R01-SMOKE-4-V1` / `-GEPA-R01-SMOKE-4-FIT-V1` and `-GEPA-R01-SMOKE-4-TWIN-V1` / `-GEPA-R01-SMOKE-4-TWIN-FIT-V1` |

**Why new identities.** CELL-1's and CELL-2's run, attempt and fit identities are consumed; a
`(run_id, attempt_id)` pair is a one-time key and a plan budget is run-cumulative across every
attempt of one run id. CELL-1-GEPA is a sibling fragment set, not an edit of CELL-1's or CELL-2's
files, and neither is touched by this registration.

### 2a. The algorithm label: three operators

`core.base.STAGE3_ALGORITHMS` registers `gepa-reflective-pareto-v1` with operators
`credit_assignment` / `update` / `selection` / `context_application`. The fragments declare
`["update", "selection", "context_application"]`: the proposer cell rewrote each node's guidance
text by reflecting on the sealed ROLL-1 trajectories (UPDATE), the decision-83 frontier rule chose
the survivors at curation (SELECTION), and the per-node `context_supply` route that puts those
statements into a row is the context-application step (CONTEXT_APPLICATION), the same operator the
Training-Free GRPO family declares for the same route. `credit_assignment` is not declared here
because this cell performs none: it consumes a released store.

History: the registration agent's first draft declared two operators because the registry record
lacked `context_application`; the coordinator amended the record on 2026-09-24 (before any flip or
contact) so that every family that applies a released store by candidate-bound supply carries the
same application operator and the three arms stay comparable by construction (owner decision 101).
`scripts/checks/stage3_algorithm_label_check.py` passes with the three operators.

## 3. Decision rule (fixed here, owner decision 99: the TRAIN lock)

Delta = CELL-1-GEPA minus the sealed PLAN arm, in percentage points.

- **ADMITTED** -- the CI95 lower bound of the paired **official pooled SLU-F1** delta is **above
  zero** and the CI95 lower bound of the paired **intent** delta exceeds **-0.9943**. A gain is
  proven, not merely non-inferior.
- **NEUTRAL** -- both guards non-inferior (SLU lower bound above -1.2485, intent lower bound above
  -0.9943) without a proven SLU gain.
- **HARMFUL** -- a **measured** loss on either guard (owner decision 25, Method B: a CI95 upper
  bound below zero, or a point estimate beyond the margin). Width alone is NEUTRAL, never HARMFUL.
- **TWIN = attribution, never admission.** A gain the twin reproduces within the plan's own null is
  **form** -- the store's shape and token volume -- not content, and the verdict says so and claims
  no content effect. This store is the LONGEST of the family so far (7,345 authored tokens against
  v1r's 5,740 and v2's 3,001), so a form effect is a live alternative explanation for any movement
  and the twin is what separates them.
- **SECOND LOOK, partial** -- see section 3a.
- **Per-scenario harm bound** (owner decision 17) and **frontier row** (owner decision 75) as for
  CELL-1, diagnostics beside the verdict, never gates.
- **Delta-consumption table** (item S3-4s) -- per node, per scenario **and per value provenance**
  (GEPA-authored or iteration-1 retained), placed beside CELL-1's own table, with the **Planner
  route reported separately**, never pooled.
- **Replication** -- an ADMITTED result is replicated on the **same roster** and then on a **fresh**
  one before any DEV, Fold B or test read. No such read is authorised by this package.
- **NOT READ HERE: GEPA against Training-Free GRPO.** Three arms on one comparator, one population,
  one own null and one estimator make that comparison possible, and making it is a separate read
  with its own preregistration naming the estimand, the multiplicity treatment over three families
  and the roster the claim is made on.

The read is executed by script (owner decision 58): `scripts/flights/batch/gepacell_read.sh
arm|twin`, which drives `scripts/analysis/plan_cell_read.py` with `--registered
docs/readiness/2026-09-24-slurp-stage3-delta-cell-gepa-r01-v1/registered-facts-v1.json` and `--h-slu
1.2485 --h-intent 0.9943`. The exact invocations are in `analysis-recipe-v1.json` under `driver`.

### 3a. This is PARTLY a second look, and the verdict says so

Two populations meet in this store:

- the **248 GEPA-authored rows** were built only from R01C construction rows. The release
  registration pins TRAIN Fold A, TRAIN Fold B and DEV-1000 as `forbidden_rosters` and
  `core.semantic_knowledge_preparation.prepare_semantic_knowledge_store` verified each by SHA-256 at
  release time, so no evaluated row of this cell's population contributed one of them;
- the **200 retained rows** were kept by applying the decision-83 rule to **CELL-1's own
  per-scenario and per-delta read of TRAIN Fold A** -- these same 1,080 rows.

So the rows that chose part of the store are the rows the store is measured on, and:

- CELL-1-GEPA's verdict is a **development number** under owner decisions 28 and 86, and is not an
  independent confirmation of anything;
- an ADMITTED CELL-1-GEPA does **not** authorise a claim: the **replicate on a fresh roster (TRAIN
  Fold B or DEV)** precedes any effectiveness claim, and that replicate needs its own registration;
- the per-provenance delta-consumption table is what keeps the two apart in the read: if the
  movement is carried by the 248 GEPA-authored rows, the second-look caveat binds weakly; if it is
  carried by the 200 retained rows, it binds hard, and the verdict must say which.

## 4. Smoke acceptance (four rows, structural only)

Beyond the standard list (4 rows delivered, no tools array, every request fits, dispositions
counted, one normaliser receipt per row, the Perception request differing from the comparator's by
exactly the added block), the structural rule for CELL-1-GEPA's smoke is **the realised per-node
supplied counts equal the offline dry run's**, row by row, on both forms.

### 4a. The registered offline dry run

`analysis.native_episode_dry_run` walked the registered CELL-1-GEPA smoke composition on the REAL
released GEPA stores, contact-free, on **all four rows** with the Perception candidate ids the flight
itself produced (read off the retired CELL-1 v2 smoke attempt's own trace -- the same four rows),
plus a REVISE revisit and a duplicate-candidate row. Driver
`scripts/flights/batch/gepacell_dry_run.py`; full record
`docs/readiness/2026-09-24-slurp-stage3-delta-cell-gepa-r01-v1/dry-run-v1.md`. **Both forms PASS.**

| row | arm S / R / Pl | twin S / R / Pl |
| --- | --- | --- |
| `slurp:train:000007:audio--1504197557` | 8 / 4 / 4 | 8 / 4 / 4 |
| `slurp:train:000009:audio-1497557594-headset` | 1 / 4 / 4 | 4 / 3 / 2 |
| `slurp:train:000015:audio-1488524781` | 5 / 4 / 4 | 5 / 4 / 2 |
| `slurp:train:000023:audio-1490956038` | 0 / 0 / 0 | 0 / 0 / 0 |

(S = Solver cap 8, R = Reviewer cap 4, Pl = Planner cap 4. The Perception unconditional slice is
**seeded** before the walk rather than supplied at a node boundary, so it is not in these columns;
its four value ids are **measured to be the same four** as v1r's and v2's, because all four are
retained and no GEPA-authored perception row outranks them by `prior_score` descending / `value_id`
ascending.)

Every walk completes the whole graph (perception -> solver -> reviewer -> planner, delivery from the
Solver's sealed draft) on every row, on both forms. The duplicate-candidate row (n=3, distinct=1 --
the shape that aborted the CELL-1 arm after 304 metered contacts) walks, with 3 candidate
projections receipted.

**Three things this dry run establishes that CELL-2's did not.**

1. **The routes serve, at cap, on three of four rows.** Where CELL-2's retained store selected
   almost nothing on this roster, the GEPA store fills the Reviewer and Planner caps on every row
   that matches at all. The risk this cell reports is therefore not inertness but volume.
2. **Row `slurp:train:000023:audio-1490956038` declines all three candidate-bound routes on both
   forms.** Its Perception candidates are `iot_hue_lightdim` / `iot_hue_lighton` /
   `iot_hue_lightoff`, which reach no value in the store (the released reach block covers
   `iot_hue_lightchange`, `iot_hue_lightup` and `iot_wemo_off`). Each declined route is receipted
   with its reason. Four rows cannot decide whether a route is inert at population level -- the
   1,080-row arm's own delta-consumption table does (the B9a-rec lesson) -- so this is the
   registered expectation, reported and never failed.
3. **A REVISE revisit acquires a SECOND, DISJOINT slice, not nothing.** Registered before contact,
   and a deliberate correction of the rule CELL-2's driver carried. A candidate-bound route excludes
   what the accumulated `QueryState` already holds and then fills its cap from what is left, so at a
   448-value store a revisited node acquires more; the dry run measures arm Solver 1 / Reviewer 4 /
   Planner 4 and twin Solver 4 / Reviewer 4 / Planner 0 on the second visit, with 25 (arm) and 24
   (twin) distinct delta value ids over the episode and **zero duplicate acquisitions**. At CELL-2's
   200-value store there was no second slice to find, so "acquires nothing" and "acquires nothing it
   already holds" could not be told apart there. The invariant that matters is unchanged:
   `QueryState` refuses a duplicate `retrieved_value_id`,
   `EvidenceAgentController._acquired_ids` refuses such a decision and the trajectory dies (the
   2026-09-17 cell B1 abort). The driver therefore fails on an OVERLAP and reports the second
   slice's size. The consequence is a cost, not a defect: a revised row carries more delta text,
   which the E20 compaction count and the frontier row's token basis both report.

**The arm and the twin are not expected to match per node.** The derangement moves each row's whole
attachment tuple, so a candidate-bound route selects a different slice; only the store's total
authored token count is held, never the supplied volume. The dry run already measures different
counts on three of four rows (arm items 0 / 14 / 12 / 12 per perception / solver / reviewer /
planner, twin 0 / 17 / 11 / 8), and the read reports both sides rather than asserting an identity.

**The Planner slice is this cell's own open question.** It grows from CELL-1's 14 values over 4
intents to 77 over 33, 73 of them GEPA-authored, and CELL-1 measured that route at 0.594 of rows
supplied, 1.259 items per supplied row and **never at cap**. The dry run shows it at cap on three of
four smoke rows. Whether that holds over 1,080 rows -- and whether it helps -- is reported
separately, never pooled.

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

Every number is cell PLAN's, CELL-1's and CELL-2's own registered ceiling, unchanged: this cell is
the locked plan plus one store, so its role graph and its per-row ceiling are PLAN's.

**Cost, registered before contact.** CELL-1 realised 4,553 contacts (4.216 per row), 9,264.9
prefilled tokens per row and 1.8021 GPU hours per 1,080; the sealed PLAN arm realised 4,424 contacts
(4.096 per row), 8,353.2 tokens per row and 1.7579 GPU-h. This store supplies **more** than v1r at
every node -- worst-case supplied characters per node 528 / 1,035 / 471 / 479 against v1r's 485 /
938 / 423 / 381 and v2's 476 / 850 / 416 / 269 -- with fuller reach, so more rows fill a
candidate-bound cap and a revised row acquires a second slice. **The registered expectation is
therefore that the prefill rises ABOVE CELL-1's 9,264.9 tokens per row, and CELL-1's figures are
reported as the predecessor row of the frontier table rather than as this cell's bound.** The
contact count is expected to hold at cell PLAN's 4.0963 per row because the role graph does not
move. Every realised number is MEASURED, never predicted. Ceilings are bounds, never targets;
budgets are run-cumulative across every attempt of a run id.

**Fit.** `native_contact_fit`, fitted inside the same flight under the same lease. `coordinate-fit`
must **not** be run. Each cell carries its OWN fit identity (item E16), and a recovery
re-registration needs **both** a new generation attempt id **and** a new
`native_contact_fit.attempt_id` in the baseline -- the rule CELL-1 learned by losing two relaunches
to a fit identity that already carried evidence.

**Prompt fit: NOT MEASURED IN THIS REGISTRATION.** `core.flight.cli check`'s `_assess_prompt_budget`
is the measurement and it runs in the coordinator's own clean-tree re-pin cycle against the minted
receipt; the registering agent did not run it (section 9). What is measured here, model-free from
the released authored document, is the worst case each node can render at the unchanged caps:

| phase | worst-case supplied chars (GEPA) | v1r | v2 | CELL-2's measured token bound | expected |
| --- | ---: | ---: | ---: | ---: | --- |
| perception | 528 | 485 | 476 | 19,992 (ALLOW) | ALLOW |
| reviewer | 471 | 423 | 416 | 19,856 (ALLOW) | ALLOW |
| planner | 479 | 381 | 269 | 19,795 (ALLOW) | ALLOW |
| **solver** | **1,035** | 938 | 850 | **21,821 (COMPACT_REQUIRED, -317)** | **COMPACT_REQUIRED** |

against the 24,576-token live slot less its one-eighth (3,072) reserve. The longest single statement
is 140 characters (126 at v1r and v2) and the mean is 88.9. At roughly 3.5 characters per token the
bound is expected to be CELL-2's plus about +15 / +53 / +16 / +60 tokens -- an **estimate**, written
down so that a surprise in the coordinator's check reads as a surprise. The episode declares
`context_fit_policy` `compact-or-abstain`, so a Solver request that really exceeds the window is
compacted, never truncated, and every compaction is counted in the E20 receipts (CELL-1 compacted
zero rows). If the check reports a BLOCKER rather than COMPACT_REQUIRED, the cell does not open and
the per-node caps are the thing to reconsider -- not the reserve.

## 6. Boundary

The store's `source_sample_ids` are **201 R01C construction utterances** (`source_split_identity_hash`
`7c603857...c46d7`), all inside the 225-row ADV-1 disagreeing roster that v1r and v2 also pin. The
release registrations pin **TRAIN Fold A**, **TRAIN Fold B** and **DEV-1000** as `forbidden_rosters`
and the preparer verified each by SHA-256 at release time. No evaluated row of this cell's own
population contributed a delta. No gold label, reference transcript, delivered answer or future turn
enters runtime. TRAIN Fold A is the roster the sealed PLAN arm, CELL-1 and CELL-2 already flew, so
this cell opens **no new speech identity**. TRAIN Fold B, DEV-1000, DEV-2000, DEV-2000-ADDED and the
test split stay untouched and unread.

## 7. What is registered

Package `docs/readiness/2026-09-24-slurp-stage3-delta-cell-gepa-r01-v1/`:

| file | what |
| --- | --- |
| `README.md` | the engineering record: the store, the derivation from CELL-1, the dry run and the proofs |
| `protocol-registered-v1.json` | the registered protocol (factor, twin, store facts, provenance, population, decision rule, accounting, fit, prompt fit, boundary, smoke acceptance, revisit rule) |
| `registered-facts-v1.json` | the facts `scripts/analysis/plan_cell_read.py` reads against (`--registered`) |
| `analysis-recipe-v1.json` | the read: driver, stages, exact arm and twin invocations, tables, diagnostics, and what is NOT read here |
| `dry-run-v1.md` | the offline four-row native-episode dry run, both forms, zero contacts |
| `generation-plan-registered-v1.json` | arm generation plan |
| `fit-plan-registered-v1.json` | arm native-contact-fit plan |
| `twin-generation-plan-registered-v1.json` | twin generation plan |
| `twin-fit-plan-registered-v1.json` | twin native-contact-fit plan |
| `smoke-generation-plan-registered-v1.json` | smoke generation plan |
| `smoke-fit-plan-registered-v1.json` | smoke native-contact-fit plan |
| `twin-smoke-generation-plan-registered-v1.json` | twin smoke generation plan |
| `twin-smoke-fit-plan-registered-v1.json` | twin smoke native-contact-fit plan |

plus the campaign plans `configs/campaign/slurp-native-stage3-delta-cell-gepa-r01-v1.json` and
`...-gepa-r01-twin-v1.json`, the six config fragments (four baselines and two experiment fragments),
**eight** unconsumed DRAFT exposure-ledger rows, and the runbooks
`scripts/flights/batch/gepacell_repin_{smoke,twin_smoke,arm,twin}.sh`, `gepacell_flip_all.sh`,
`batch_chain_gepacell.sh`, `gepacell_read.sh` and `gepacell_dry_run.py`.

**The two release registrations are REFERENCED, not copied**:
`docs/readiness/2026-09-24-slurp-stage3-gepa-r01-v1/stage3-deltas-gepa-v1-release-registration.json`
(sha256 `cbcf18d4...`) and `...-twin-v1-release-registration.json` (sha256 `f4fa1332...`) stay in the
GEPA proposer package, where the release that produced them recorded them --
`core.semantic_knowledge_preparation` records a registration by its repo-relative path and the
released `release.json` binds exactly that path, so a copy would be a second file to keep true for
no gain.

### 7a. How CELL-1-GEPA differs from CELL-2, and why

1. **Store pins** point at `knowledge/slurp/semantic/stage3-deltas-gepa{,-twin}-v1/` in all four
   baselines; every other decided key is CELL-2's byte for byte, so the one-factor property against
   the locked plan holds by construction.
2. **Identities**: eight new run ids, four new attempt ids, four new fit identities. Nothing of
   CELL-1's or CELL-2's is reused or rewritten.
3. **The algorithm label** is `gepa-reflective-pareto-v1` with `["update", "selection"]` -- see
   section 2a for the operator the registry will not let this cell declare.
4. **The decision receipt is `cell-admission-v1.json`, not `root-admission-v1.json`** -- see section
   10. The coordination directory `coordination/slurp-stage3-delta-cell-gepa-r01-v1/` already holds
   the GEPA PROPOSER cell's `root-admission-v1.json` (decision id
   `slurp-stage3-gepa-r01-admission-v1`) and its release pins, and two receipts cannot share one
   path. Every fragment, plan and runbook in this package already names
   `cell-admission-v1.json`.
5. **The dry-run driver's REVISE rule** is disjointness, not emptiness (section 4a).
6. **The smoke plan documents name the real baseline fragments.** CELL-2's smoke plans carried
   `slurp-native-stage3-delta-cell-r02-smoke-4-v1-baseline-v1`, a name no file has; this package
   writes `slurp-native-stage3-delta-cell-gepa-r01-smoke-4-baseline-v1` and
   `...-twin-smoke-4-baseline-v1`. The field is documentary, but a documentary field that names no
   file is a defect.
7. **`prepared_phase_supply` is absent** from all four baselines (the cell-P0 form), and **no
   decision requirement** is registered in either fragment: `repin_cell.py` inserts both at the
   flip, and a placeholder without an `expected_decision_id` would refuse the campaign at load.
8. **CELL-2's own launch history is not carried.** The `defect_and_fix`, `repin_obligation` and
   `supersedes` blocks of CELL-2's smoke plans describe CELL-2's three retired run ids; this cell has
   no launch history and claims none.

## 8. Registered hashes

| run id | cell | plan | composed config | protocol hash | split identity |
| --- | --- | --- | --- | --- | --- |
| `SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-V1` | `...-gepa-r01-v1` | `generation-plan-registered-v1.json` | `a7853c3f45b115ff60d64ecc42d7733e6546e4a7c7729f8bb772c92f3b8f48d2` | `ac06f785d76d4ceb9e0200e3527a7558d70ed3c89587e0bb41c6ec7172682ede` | `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6` |
| `SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-FIT-V1` | `...-gepa-r01-fit-v1` | `fit-plan-registered-v1.json` | same | same | same |
| `SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-TWIN-V1` | `...-gepa-r01-twin-v1` | `twin-generation-plan-registered-v1.json` | `fce42bd1812ebb7b4fdfa843722d2d9258c9ceba1d5f59ef4f759cbc1b435670` | `3e9bd26ca5f183e02eede45527928f81d7626c78c8251d81891da65bdaa5ed80` | same |
| `SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-TWIN-FIT-V1` | `...-gepa-r01-twin-fit-v1` | `twin-fit-plan-registered-v1.json` | same | same | same |
| `SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-SMOKE-4-V1` | `...-gepa-r01-smoke-4-v1` | `smoke-generation-plan-registered-v1.json` | `5be01487d8037ea757e011bc62ce4e8bac9c484d6c5a2784fbc654eb3bb6e839` | `023c497a43ac1d22699a45fdbc6b544cf517bc3f8d689e270e6962937fff4a30` | `4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb` |
| `SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-SMOKE-4-FIT-V1` | `...-gepa-r01-smoke-4-fit-v1` | `smoke-fit-plan-registered-v1.json` | same | same | same |
| `SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-SMOKE-4-TWIN-V1` | `...-gepa-r01-smoke-4-twin-v1` | `twin-smoke-generation-plan-registered-v1.json` | `7e08dcb26c04d6bad5cb0e303364609bb75714f53a6c1145fc907d6d22d59a1c` | `fab28bae8a3f33b37c6fa912b2039410d025d48c9ec0f7fcc6b21e85a564822e` | same |
| `SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-SMOKE-4-TWIN-FIT-V1` | `...-gepa-r01-smoke-4-twin-fit-v1` | `twin-smoke-fit-plan-registered-v1.json` | same | same | same |

Protocol document `protocol-registered-v1.json` sha256
`1404b5c70cc74220df4fa35e74363577f4cc8ca623d63f8e580a8e96b6265245`.

Every hash above was computed offline by `core.config.compose` and `core.config.protocol_hash` over
the committed fragments, exactly as `scripts/flights/batch/e35_rehash.py` does. **`core.flight.cli
check` was NOT run** -- it needs the coordinator's clean-tree cycle and the minted receipt, and it is
where `prepared_artifacts_ok`, the readiness state and the prompt-fit bound are established.
**Every one of these hashes moves at the readiness flip** (the flip edits the readiness block, which
`compose()` hashes), and `scripts/flights/repin_cell.py` -- driven by `repin_loop_generic.sh` --
rewrites the plans, this note, the README and the exposure rows in dependency order.

## 9. What this registration does NOT authorise (readiness held)

`readiness.state` is `"held"` on all eight cells. No decision id is minted, no
`scripts/flights/repin_cell.py --set-ready` has run, no `core.flight.cli check` has run, no exposure
row is countersigned (all eight read `consumed = no` and carry `REGISTERED BEFORE CONTACT (draft,
root countersignature pending)`), and no cell is on the batch queue. **No model, tokenizer, encoder,
ASR, scorer, server, GPU, network or paid-API contact was made by this registration**, and it made
no write to the data root at all: the GEPA stores were released before it began.

Also not authorised: any DEV, TRAIN Fold B or test read; the same-roster replicate; a GEPA iteration
2 of the store; any edit of a released store (versions 1, 1r, 2, the GEPA store and every twin of
them are read-only and pinned by SHA-256 here); any re-flight or re-read of CELL-1 or CELL-2; any
comparison of GEPA against Training-Free GRPO or ACE; and any amendment of
`core.base.STAGE3_ALGORITHMS`.

## 10. The coordinator's sequence

On the main checkout, after merging `fable/gepacell`. Nothing below was performed by the registering
agent.

**0. The receipt file name.** `coordination/slurp-stage3-delta-cell-gepa-r01-v1/` already contains
`root-admission-v1.json` -- the GEPA PROPOSER cell's admission receipt (decision id
`slurp-stage3-gepa-r01-admission-v1`) -- alongside `stage3-deltas-gepa-v1-release-pins.json`,
`gepa-dry-run-v1.json` and `gepa-prompt-size-scan-v1.json`. This cell's receipt is therefore
**`cell-admission-v1.json`**, and every fragment, plan document, runbook and exposure row in this
package names that path. `scripts/flights/batch/mint_decision_receipt.py` hard-codes
`root-admission-v1.json` as its output name, so it would OVERWRITE the proposer's receipt. The
minimal safe recipe:

```
cd $SPEECHRL_DATA_DIR/coordination/slurp-stage3-delta-cell-gepa-r01-v1
cp root-admission-v1.json root-admission-v1.json.proposer-backup
# ... mint (step 1) ...
mv root-admission-v1.json cell-admission-v1.json
mv root-admission-v1.json.proposer-backup root-admission-v1.json
```

The durable fix is an `--out-name` flag on the minting tool; it is not taken here because a shared
tool is not edited during a live flight.

**1. Mint the decision receipt** from the CELL-2 receipt (WSL, from the study root):

```
python scripts/flights/batch/mint_decision_receipt.py \
  --from stage3-delta-cell-r02 --from-tag STAGE3-DELTA-CELL-R02 --from-date 2026-09-24 \
  --name stage3-delta-cell-gepa-r01 --tag STAGE3-DELTA-CELL-GEPA-R01 --date 2026-09-24 \
  --expected-contacts 4553 --expected-gpu-hours 1.85 \
  --replace 'SAEA-SLURP-STAGE3-DELTA-CELL-R02-=SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-' \
  --replace 'knowledge/slurp/semantic/stage3-deltas-twin-v2=knowledge/slurp/semantic/stage3-deltas-gepa-twin-v1' \
  --replace 'knowledge/slurp/semantic/stage3-deltas-v2=knowledge/slurp/semantic/stage3-deltas-gepa-v1' \
  --replace 'b81df5c5175e45e68933d4875c110fd46bea933283631d2c428187c480fc31f0=53c1267169b5269bc850f75527b2c8086fd681126f9180ac4a0df9410b61fcfa' \
  --replace '44a804184cf83a08e85831d40bae942af1e71ed4365b485d833f9a03807ef150=560d84e7e6364de5ce09635f586660d22b9a103734c51dbd64e6182599fb935c' \
  --replace 'b18b141f67dae4b413391d22dd787a3b85480d2b4fab24db0848e547e7aa1a9a=fb2dad3082848f1ff794401f2ea1d9b0d53e33b0f7a459592b44364cce196fb3' \
  --replace '131809122d23ccdaac86c9a9426c5e045a9544fc3059c1b46f80a3365151d614=f19671d381f82ffb07f7d186b93c45adfe129bcf934e62011abdec1744123ffe' \
  --decision "<one sentence: what is admitted>" \
  --authority "<owner decisions 83 / 99 / 101 / 106; spec S3-6 and the GEPA arm design; the sealed GEPA proposer cell and its released store>" \
  --claim-boundary "<TRAIN development numbers; PARTLY a second look, because 200 of the 448 values were retained on these rows; the twin decides attribution, never admission; no DEV, Fold B or test read; no GEPA-versus-TF-GRPO comparison>"
```

The `--replace` pairs are applied **in order**, after the tool's own five id substitutions (which
already rewrite `slurp-stage3-delta-cell-r02-admission-v1`, every
`slurp-native-stage3-delta-cell-r02-` prefix -- cell ids, baseline fragment names and attempt ids --
the readiness directory and the coordination directory). The twin store path always precedes the
non-twin path it contains. **The two split identities need no substitution**: the CELL-2 receipt
already names TRAIN Fold A (`61b0f062...`) and the four-row smoke split (`4e3413fe...`), which are
CELL-1-GEPA's own. Check after minting that no `R02`, `r02`, `-v2/`, `b81df5c5`, `b18b141f`,
`44a80418` or `13180912` substring survives, and that `decision_id` is
`slurp-stage3-delta-cell-gepa-r01-admission-v1`.

**1b. Three fields the tool cannot set.** After the rename of step 0, on the data root:

```
python - <<'PY'
import io, json, os
p = os.environ["SPEECHRL_DATA_DIR"] + "/coordination/slurp-stage3-delta-cell-gepa-r01-v1/cell-admission-v1.json"
d = json.load(io.open(p, encoding="utf-8"))
d["eligible_run_ids"] = [
    "SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-SMOKE-4-V1", "SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-SMOKE-4-FIT-V1",
    "SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-SMOKE-4-TWIN-V1", "SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-SMOKE-4-TWIN-FIT-V1",
    "SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-V1", "SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-FIT-V1",
    "SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-TWIN-V1", "SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-TWIN-FIT-V1"]
d["budget"]["arm"].update({"generation_calls_cap": 11880, "fit_endpoint_calls_cap": 47520,
                           "repeated_speech_audio_seconds_cap": 33930, "gpu_hours_fit_inclusive_cap": 12.0,
                           "native_task_contract_calls_cap": 6480, "official_complete_score_jobs": 1,
                           "ceiling_note": "11 contacts per row = 1 + 2 x (3 + 1 + 1), the locked plan's own"})
d["budget"]["smoke"].update({"generation_calls_cap": 44, "fit_endpoint_calls_cap": 176,
                             "repeated_speech_audio_seconds_cap": 117, "gpu_hours_fit_inclusive_cap": 1.0,
                             "native_task_contract_calls_cap": 24, "official_complete_score_jobs": 0})
d["registered_hashes"].update({
    "arm_composed_config": "a7853c3f45b115ff60d64ecc42d7733e6546e4a7c7729f8bb772c92f3b8f48d2",
    "arm_protocol": "ac06f785d76d4ceb9e0200e3527a7558d70ed3c89587e0bb41c6ec7172682ede",
    "smoke_composed_config": "5be01487d8037ea757e011bc62ce4e8bac9c484d6c5a2784fbc654eb3bb6e839",
    "smoke_protocol": "023c497a43ac1d22699a45fdbc6b544cf517bc3f8d689e270e6962937fff4a30"})
d["cell_kind"] = ("Stage-3 S3-6 one-factor knowledge cell, the GEPA family (owner decision 101): the locked "
                  "v2.0 plan plus the released 448-value stage3-deltas-gepa-v1 store, read against the sealed "
                  "PLAN arm at the plan's own null, with a derangement twin as the form control. PARTLY a "
                  "second look: 200 of the 448 values were retained on these same TRAIN Fold A rows.")
io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=2) + "\n")
PY
```

Check after minting that `eligible_run_ids` names exactly the eight ids above and that `population`
still describes TRAIN Fold A 1,080 and the four-row smoke.

**2. Flip the four generation cells** -- smoke, twin smoke, arm, twin -- one cycle each, on the clean
tree:

```
bash scripts/flights/batch/gepacell_flip_all.sh
```

which drives `repin_loop_generic.sh` over `gepacell_repin_smoke.sh`, `gepacell_repin_twin_smoke.sh`,
`gepacell_repin_arm.sh` and `gepacell_repin_twin.sh`. Each pass re-pins with
`scripts/flights/repin_cell.py --set-ready`, commits, and re-runs until the freshly composed hashes
and the registered documents agree. The four FIT cells stay `held` -- they are spend identities,
never flown as generation cells. `--allow-output-change` must never be passed: the committed
baselines carry no `prepared_phase_supply` pin at all, so the flip MINTS each cell's own artifact
under its own run id (item E16), and a CHANGED output on a later re-pin means the knowledge channel
moved.

**3. Chain the flights** through the batch driver only (owner decision 77):

```
bash scripts/flights/batch/batch_chain_gepacell.sh
```

Two steps: step 1 flies the generation smoke then the 1,080-row arm; step 2 flies the twin smoke then
the 1,080-row twin. Expected rows 4 then 1,080 per step, `contacts_per_row` 4 (CELL-1 realised
4.216), `ceiling_per_row` 11, tool-free, session
`serving-slurp-native-candidate-five-train-a-np4-v1`. Each arm opens only after its own smoke seals,
and the twin never flies beside the arm. An aborted campaign leaves `locks/flight.lock` behind; clear
it before the next launch.

**4. Read**, arm first, then the twin: `bash scripts/flights/batch/gepacell_read.sh arm|twin`, as
`analysis-recipe-v1.json` records. **5. Countersign** the eight exposure rows as the flights consume
them. Do not countersign before contact.
