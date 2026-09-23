# Cell CELL-1: the locked v2.0 plan plus the per-node stage3-deltas store: preregistration

Registered 2026-09-23 by the CELL-1 registration agent (worktree `/home/chao/saea-worktrees/fable-cell1reg`,
branch `fable/cell1reg`) at study commit `56b1570b`, per
`docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md` sections S3-6 and S3-4s and owner
decisions 83, 99, 101 and 106. Before any contact. **READINESS HELD**: this registration authorises no
flight, no readiness flip, no decision receipt, no exposure-row countersignature and no contact (section 9).

## 1. Why this cell exists

Cell ROLL-1 sealed 625 construction rows; S3-3 found 225 of them disagreeing; cell ADV-1 asked the frozen core,
once per disagreeing row, what each responsible node should do differently; S3-5 curated those statements into
the append-only delta store `stage3-deltas-v1r` (379 rows) and its derangement twin. (Store **revision v1r**, 2026-09-23: the same 379
statements re-attached to the construction gold intent each was learned on. Version 1 attached each
statement's `TARGET`, which is a **slot type** on the 147 slot-contract rows, so a candidate-bound route
could reach only 121 of 379 values and only 11 of the Solver's 151; it is superseded before any flight
and was never consumed -- `stage3-deltas-v1-superseded-v1.md` in this package.) CELL-1 is the only cell of
the Training-Free GRPO loop that carries a **gating** claim (owner decision 99 order): it applies the store to
the locked v2.0 plan and asks whether the loop bought anything.

## 2. The factor and the arms

| item | value |
| --- | --- |
| base | the locked v2.0 plan, `configs/baseline/slurp-native-default-plan-lock-baseline-v1.json`, exactly as the sealed PLAN arm flew it (official 63.6304 / 82.2222) |
| factor | `knowledge_stores.stage3-deltas` and nothing else: the released store supplied per node through `context_supply` -- Perception **unconditional** cap 4 (`stage3-delta-unconditional-v1`), Solver cap 8, Reviewer cap 4, Planner cap 4 (`stage3-delta-candidate-bound-v1`, each bound to the row's own Perception candidate intents); every route `node_target`-filtered and `prior_score`-ranked |
| store | `knowledge/slurp/semantic/stage3-deltas-v1r/` -- release file `02505ba2...`, snapshot content hash `e2552666...`; 379 values (perception 119 / solver 151 / reviewer 95 / planner 14), **39 distinct facets, every one a legal intent id** (402 facet entries: 357 rows carry one, 21 carry two, 1 carries three), 223 source sample ids, mean statement 84.0 characters, longest 126 |
| twin | `knowledge/slurp/semantic/stage3-deltas-twin-v1r/` -- release file `7c0dc897...`, snapshot content hash `5aee8d1d...`; the same 379 statements, the same node distribution, the same token count (5,740) and the same per-row facet-count multiset, facet attachment and unconditional TARGET fields deranged under seed 20260922 as **whole attachment tuples**; 16 of 379 rows landed on an equal facet set by arithmetic (39 distinct intents over 379 rows) and are reported, not refused |
| population | TRAIN Fold A, 1,080 rows, split identity `61b0f062...5398b6`; the smokes read the first four rows, split identity `4e3413fe...b969cb` (cell PLAN's own smoke population) |
| comparator | the sealed PLAN arm `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1`, attempt `attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1`, **never re-flown** |
| margins | the plan's own null (PLAN vs PLANr): **h_SLU 1.2485, h_intent 0.9943** |
| contacts per row | ceiling **11**, the locked plan's own program maximum; the store adds supplied text to requests the plan already makes and adds no contact |
| session | `serving-slurp-native-candidate-five-train-a-np4-v1` (resident; attach only, never spawn or stop) |
| Stage-3 algorithm (decision 101) | `tfgrpo-semantic-advantage-v1`, operators `update` + `context_application` |
| runs | arm `SAEA-SLURP-STAGE3-DELTA-CELL-R01-V1` / `-R01-FIT-V1`; twin `-TWIN-V1` / `-TWIN-FIT-V1`; smokes `-SMOKE-4-V1` / `-SMOKE-4-FIT-V1` and `-SMOKE-4-TWIN-V1` / `-SMOKE-4-TWIN-FIT-V1` |

## 3. Decision rule (fixed here, owner decision 99: the TRAIN lock)

Delta = CELL-1 minus the sealed PLAN arm, in percentage points.

- **ADMITTED** -- the CI95 lower bound of the paired **official pooled SLU-F1** delta is **above zero** and the
  CI95 lower bound of the paired **intent** delta exceeds **-0.9943**. A gain is proven, not merely non-inferior.
- **NEUTRAL** -- both guards non-inferior (SLU lower bound above -1.2485, intent lower bound above -0.9943)
  without a proven SLU gain.
- **HARMFUL** -- a **measured** loss on either guard (owner decision 25, Method B: a CI95 upper bound below zero,
  or a point estimate beyond the margin). Width alone is NEUTRAL, never HARMFUL.
- **TWIN = attribution, never admission.** The twin arm is read with the same estimator, the same seed and the
  same sealed comparator. A gain the twin reproduces within the plan's own null is **form** -- the store's shape
  and token volume -- not content, and the verdict says so and claims no content effect. A gain the twin does not
  reproduce is attributed to the deltas' content, with the twin delta reported beside it.
- **Per-scenario harm bound** (owner decision 17) -- per-scenario intent and SLU over all 18 scenarios in BOTH
  the natural-mixture and the equal-stratum weighting, with net harmed rows per scenario and any scenario of five
  or more flagged. A diagnostic beside the verdict, never a gate.
- **Frontier row** (owner decision 75) -- official SLU-F1 delta x prefilled tokens per row x GPU hours per 1,080
  rows, for the arm and for the twin, placed beside the registered rows.
- **Delta-consumption table** (item S3-4s) -- per node and per scenario: rows supplied, items per row against the
  cap, the distinct `value_id`s supplied, and the saves / harms / ties on the rows that received each one. A
  primary deliverable whatever the verdict; it is what decides store version 2. Value ids, node targets, facet ids
  and counts only, never statement text.
- **Replication** -- an ADMITTED result is replicated on the **same roster** before any DEV, Fold B or test read.
  No such read is authorised by this package.

The read is executed by script (owner decision 58): `scripts/analysis/plan_cell_read.py` against the sealed PLAN
arm, with `--registered docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1/registered-facts-v1.json` and
`--h-slu 1.2485 --h-intent 0.9943`. The exact invocations are in `analysis-recipe-v1.json` under `driver`.

## 4. Smoke acceptance (four rows, structural only)

A failed smoke stops its own arm. Beyond the standard list (4 rows delivered, no tools array, every request fits,
dispositions counted, one normaliser receipt per row, Perception request differing from the comparator's by
exactly the added block):

**the four routes must actually serve.** Per contact, the selection receipt names the supplied `value_id`s, the
node pool size and the cap. A route that serves zero items on every row is an inert route and a FORM defect that
stops the arm -- the B9a-rec lesson (18 ACQUIRE rows, 0 items each). The smoke also reads its own **E20 compaction
receipts** per phase, because the registered worst-case bound puts the Solver phase at `COMPACT_REQUIRED` (section
5); a non-zero compacted-row count is a cost and a caveat, an abstention caused by compaction is a failure.

### 4a. A registered expectation about reach, measured model-free before contact

A candidate-bound route matches a value only when one of its `associated_facet_ids` **equals** one of the row's
Perception candidate intent ids. Intersecting the released store against the 60 registered candidate intents of
`prepared/SAEA-SLURP-NATIVE-CANDIDATE-CONTRACTS-PREPARE-V1/catalog.json` gives the upper bound on what each route
can ever select:

| node | values | reachable by a candidate intent | distinct intents covered |
| --- | --- | --- | --- |
| perception (unconditional) | 119 | all 119 eligible; the cap-4 slice is identical on every row | -- |
| solver (cap 8) | 151 | **11 (7.3 %)** | 8 |
| reviewer (cap 4) | 95 | 24 (25.3 %) | 13 |
| planner (cap 4) | 14 | 6 (42.9 %) | 6 |
| total | 379 | 121 (31.9 %) | -- |

The Solver route -- the one carrying the most deltas -- is the narrowest, because S3-5's curation wrote the **slot
type** into `TARGET` for the 147 slot-contract rows while the route intersects `TARGET` against `scenario_action`
intent ids. This is registered as an **expectation**, not repaired here: the smoke measures the realised reach, and
if the Solver route is inert the verdict says so and attributes whatever effect exists to the other three routes,
and store version 2 fixes the TARGET vocabulary rather than the supply route.

**Twin token-matching caveat.** The builder holds `authored_token_count(twin) == authored_token_count(parent)` over
the whole store and holds the node distribution exactly, but the *supplied* volume need not match: the derangement
moves facet attachment, and the measured reach already differs (arm Solver 11 against twin Solver 22). The smoke
therefore measures the per-node supplied item counts on the same four rows, and the verdict reports the realised
supplied-token delta between arm and twin rather than assuming it is zero. A twin that supplies materially more or
less than the arm is a weaker form control and the verdict says so.

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

Every number is cell PLAN's own registered ceiling, unchanged: this cell is the locked plan plus one store, so its
role graph -- and therefore its per-row ceiling -- is PLAN's. The 11 comes from
`configs/policy/phase-native-candidates-review-revise-v1.json` (`max_contacts` 11), which
`rails.native_episode_config.load_native_episode_config` resolves from the unchanged role graph perception 1 /
solver 1 / reviewer 3 / planner 1 with `max_revisions` 1 as 1 + 2 x (3 + 1 + 1).

**Expected cost**, from cell PLAN's own sealed efficiency
(`analysis/SAEA-SLURP-DEFAULT-PLAN-LOCK-PAIRED-ANALYSIS-V1/efficiency.json`): 4,424 contacts (4.0963 per row),
8,353.2 prefilled tokens per row, **1.7579 GPU hours per 1,080 rows**, 39.92 contacts per minute. This cell makes
the same contacts with longer prompts, so the contact count is expected to hold and the prefill to rise; the twin
costs the same as the arm, its token count being held exactly. Arm plus twin is the engineering spec's 3.6 GPU-h
point estimate. Ceilings are bounds, never targets; budgets are run-cumulative across every attempt of a run id.

**Fit.** `native_contact_fit`, fitted inside the same flight under the same lease. `coordinate-fit` must **not**
be run. Each cell carries its OWN fit identity (item E16): the gate refuses a request-fit receipt path that
already exists, and every one of cell PLAN's exists.

**Prompt fit, measured on the committed tree** by `core.flight.cli check` (exit 0 on all six cells). The numbers
are the runtime's own **worst-case bound** over what the supplied stores can render, not a prediction:

| phase | decision | required window tokens | operational margin |
| --- | --- | --- | --- |
| perception | ALLOW | 19,992 | +1,512 |
| reviewer | ALLOW | 19,856 | +1,648 |
| planner | ALLOW | 19,795 | +1,709 |
| **solver** | **COMPACT_REQUIRED** | 21,821 | **-317** |

against the 24,576-token live slot less its one-eighth (3,072) reserve; identical on the twin and within one token
on the smokes. `check` reports no blocker and authorises every cell. The episode declares `context_fit_policy`
`compact-or-abstain`, so a Solver request that really exceeds the window is **compacted, never truncated**, and
every compaction is counted in the E20 receipts (cell PLAN's own sealed run compacted zero rows). The same bound
could not be taken for cell PLAN for comparison: `contracts.gate_exposure` refuses `check` on a run whose exposure
row is consumed, which is correct -- so the empirical reference above is PLAN's sealed **realised** prefill
(8,353.2 tokens per row), not its bound. The authority in flight stays
`core.preparation_fit.build_native_contact_fit_gate`, which fits every realised request against the resident
tokenizer and stops rather than truncating.

## 6. Boundary

The store's `source_sample_ids` are **223 R01C construction utterances** (`source_split_identity_hash`
`7c603857...c46d7`) -- the disagreeing rows cell ADV-1 spoke about. The release registrations
(`stage3-deltas-v1-release-registration.json` and its twin) pin **TRAIN Fold A**
(`docs/receipts/rosters/slurp-evo-fold-a-v2.json`), **TRAIN Fold B** and **DEV-1000** as `forbidden_rosters`, and
`core.semantic_knowledge_preparation.prepare_semantic_knowledge_store` verifies each by SHA-256 at release time.
No evaluated row of this cell's own population contributed a delta.

No gold label, reference transcript, delivered answer or future turn enters runtime; the store carries curated
statements only. TRAIN Fold A is the roster the sealed PLAN arm already flew, so this cell opens **no new speech
identity**. TRAIN Fold B, DEV-1000, DEV-2000, DEV-2000-ADDED and the test split stay untouched and unread.

## 7. What is registered

Package `docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1/`:

| file | what |
| --- | --- |
| `README.md` | the engineering record and this registration's own section |
| `protocol-registered-v1.json` | the registered protocol (factor, twin, store facts, population, decision rule, accounting, fit, prompt fit, boundary, smoke acceptance, registration repairs) |
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
| `stage3-deltas-v1-release-registration.json` (+ twin) | the two materialised release registrations (already committed by S3-5) |

plus the campaign plans `configs/campaign/slurp-native-stage3-delta-cell-r01-v1.json` and
`...-r01-twin-v1.json`, the six config fragments, **eight** unconsumed exposure-ledger rows, and the runbooks
`scripts/flights/batch/cell1_repin_{smoke,arm,twin_smoke,twin}.sh`, `cell1_flip_all.sh`, `batch_chain_cell1.sh`.

The package carries no un-suffixed `*-plan-v1.json` twins, for the reason the ADV-1 package states: two files that
must stay in sync and prove nothing are a defect surface.

### 7a. Registration repairs (the fragments did not compose before this pass)

Each of these was measured, not assumed; the refusal is quoted in the report that accompanies this registration.

1. **The six non-prepared-supply `PENDING_<CELL>_OWN_<KEY>` tokens were filled.**
   `core.config.compose` raises `ConfigError: preparation_source_receipts must be a non-empty list` on a PENDING
   string, so neither `core.flight.cli check` nor `scripts/flights/repin_cell.py` could ever reach the preparation
   step the fill map named as their source. Every filled value except `native_contact_fit` is cell PLAN's own,
   byte for byte (`preparation_source_receipts`, the two speech-feature identity ids -- the `-smoke-v1` variants on
   the smoke baselines -- and the promotion receipt and its digest); `native_contact_fit` carries **this** cell's
   own fit run and attempt identity and its own endpoint ceiling (47,520 / 176).
2. **`prepared_phase_supply` was removed** from the four baselines rather than left as a PENDING string:
   `core.flight.repin.ArtifactPin.from_mapping` refuses a string (`malformed artifact pin`) *before*
   `ensure_artifact_pinned` can mint the real one. Removing the key is the cell-P0 form
   (`scripts/flights/batch/derive_plan_cell_registration.py` drops it for exactly this reason). The flip mints each
   cell's own pin and inserts the matching `preparation` readiness requirement. `--allow-output-change` must never
   be passed; cell PLAN's own preparation outputs are `ba5e1faa...` (1,080 rows) and `512583ec...` (4 rows), and
   this cell's added store is routed through `context_supply` rather than through the first phase's retrieval
   store, so those outputs are expected to reproduce exactly. If they do not, the knowledge channel moved: stop and
   report.
3. **`populations` was added** to the experiment fragment -- cell PLAN's own inlined 1,080 ids. Without it
   `rails.adapters.runtime_view.registered_population_ids` returns `None` and the SLURP adapter refuses every cell
   with `RuntimeViewError: runtime SLURP TRAIN samples require an explicit registered population`.
4. **The two four-row smoke cells moved into their own experiment fragment**
   `configs/experiment/slurp-native-stage3-delta-cell-smoke-4-v1.json` (population 4, split identity
   `4e3413fe...`, budgets 44 / 176 / 117 / 1.0 / 24 / 0). `registered_population_ids` resolves exactly **one**
   selection per dataset fragment, so a 1,080-row arm and a four-row smoke cannot share one fragment. This is cell
   PLAN's and cell ADV-1's own form. The arm fragment keeps four cells: the arm, the twin and their two fit
   identities.
5. **`preserve_wire_responses: true`** was added to both fragments, as every plan-family fragment carries it; the
   registered read's structural stage compares Perception request keys against the sealed comparator's preserved
   requests.
6. **The smoke fit identities** `SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-FIT-V1` and `-SMOKE-4-TWIN-FIT-V1` are named
   by the two smoke baselines' `native_contact_fit` and are declared by no cell -- cell PLAN's own form, where a
   smoke's FIT identity is a spend identity rather than a flyable cell. Each has its own registered plan document
   and its own unconsumed exposure row, so no endpoint spend can land unregistered.
7. **The four baselines' `knowledge_stores.stage3-deltas.snapshot.sha256` was corrected** from the `snapshot.json`
   **file** digest to the snapshot's **content** hash (for the version-1 release then in force: `1d55f441...` for
   the store and `d393bbbb...` for the twin).
   `rails.knowledge_stores` checks both `KnowledgeSnapshot.content_hash() == snapshot_pin["sha256"]` and
   `release["snapshot_sha256"] == snapshot_pin["sha256"]` and otherwise refuses with
   `knowledge store stage3-deltas snapshot SHA-256 mismatch`. S3-5's `cell1-fill-values.json` supplied the file
   digest (`3a770de1...` / `95c3b2aa...`) where the content hash belongs; every other store of the locked plan pins
   the content hash, which is what made the convention checkable. The **release** pin is unchanged -- it *is* the
   `release.json` file digest, and the readiness requirements that pin it were already correct.
8. **Store revision v1r (2026-09-23)** replaced the facet rule, and nothing else. The released store was mostly
   **unreachable**: a candidate-bound route (`rails/knowledge_stores.py::_stage3_delta_local_supply` ->
   `rails/stage3_delta_supply.py::select_stage3_delta_values`) selects a value only when one of its
   `associated_facet_ids` **equals** one of the row's Perception candidate **intent** ids, and S3-5's curator
   wrote `associated_facet_ids = [TARGET]` -- a **slot type** on the 147 slot-contract rows. Measured against
   the 60 registered candidate intents: solver 11 of 151, reviewer 24 of 95, planner 6 of 14, **121 of 379**
   overall. `scripts/build_slurp_stage3_delta_store.py` gained `--facet-rule`; the new schema-v2 default
   `source-intent` attaches the construction gold intent of every source row (owner decision 82) plus `TARGET`
   when `TARGET` is itself a legal intent. Same statements, same counts, same routes, same caps, same twin
   seed; **379 of 379 reachable on every node, arm and twin**. `--facet-rule target-only` reproduces version 1
   byte for byte (`3d2bc069...` / `c548b8df...`), version 1 is untouched on disk, and it was never consumed.
   Full statement: `stage3-deltas-v1-superseded-v1.md` in this package.

## 8. Registered hashes

| run id | cell | plan | composed config | protocol hash | split identity |
| --- | --- | --- | --- | --- | --- |
| `SAEA-SLURP-STAGE3-DELTA-CELL-R01-V1` | `...-r01-v1` | `generation-plan-registered-v1.json` | `063aef5c488cf90346c9ee4eecb2ebb9002057da65fec713486417aa03feeab1` | `cf4087b84e83bc5bb8604c952e202acf350ecf1eda9dfe1d7bd5388b6e5003c6` | `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6` |
| `SAEA-SLURP-STAGE3-DELTA-CELL-R01-FIT-V1` | `...-r01-fit-v1` | `fit-plan-registered-v1.json` | same | same | same |
| `SAEA-SLURP-STAGE3-DELTA-CELL-TWIN-V1` | `...-r01-twin-v1` | `twin-generation-plan-registered-v1.json` | `43f56a1020ec62e47a43c374d58d5cc2f779c115f1be99baffbbeab9b3e9380f` | `ac862b793a2f0844a6b351ae4b3b7cb9b29ea75797569035cd5a3c291d85922d` | same |
| `SAEA-SLURP-STAGE3-DELTA-CELL-TWIN-FIT-V1` | `...-r01-twin-fit-v1` | `twin-fit-plan-registered-v1.json` | same | same | same |
| `SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V1` | `...-smoke-4-v1` | `smoke-generation-plan-registered-v1.json` | `9c66586d664bfecdc9621104a09ef92cb71d94b981eaef7267fe8e7e990bf2c0` | `ae6bcef8499212e76ff1f2d0ef712b9bb902d3e865244c45c8ca4be5c4de1f39` | `4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb` |
| `SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-FIT-V1` | (spend identity) | `smoke-fit-plan-registered-v1.json` | same | same | same |
| `SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-TWIN-V1` | `...-smoke-4-twin-v1` | `twin-smoke-generation-plan-registered-v1.json` | `f98bb7a04d541b82d84d18313b0bb076c1a0e2bc03447ae79df1186f7cffe27f` | `9e3a553d39f23588273d520b084792627f46378a534e08d4e5e839019ec98f27` | same |
| `SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-TWIN-FIT-V1` | (spend identity) | `twin-smoke-fit-plan-registered-v1.json` | same | same | same |

Protocol document `protocol-registered-v1.json` sha256
`a57717c130b1636fea555cb8dc64b9cfc9bbafb666fea749f182d476996876b4`.

`core.flight.cli check` exits **0 on all six cells** on this committed tree, with the measured `config_hash` and
`protocol_hash` equal to the values above, `prepared_artifacts_ok: true` (no pin yet: the flip mints each cell's
own) and no blocker.

**Every one of these hashes moves at the readiness flip** (the flip edits the readiness block, which `compose()`
hashes), and `scripts/flights/repin_cell.py` -- driven by `repin_loop_generic.sh` -- rewrites the plans, this note,
the README and the exposure rows in dependency order.

## 9. What this registration does NOT authorise (readiness held)

`readiness.state` is `"held"` on all six cells. No decision id is minted, no `scripts/flights/repin_cell.py
--set-ready` has run, no exposure row is countersigned (all eight read `consumed = no` and carry
`REGISTERED BEFORE CONTACT (draft, root countersignature pending)`), and no cell is on the batch queue. No model,
tokenizer, encoder, ASR, scorer, server, GPU, network or paid-API contact was made by this registration.

**No decision requirement is registered in either fragment on purpose** (the ROLL-1 and ADV-1 precedent):
`core.flight.repin._upsert_decision_requirement` inserts it at the flip, and a placeholder entry without an
`expected_decision_id` would be left beside it and refuse the campaign at load
(`core.flight.campaign.declared_readiness`).

Also not authorised: any DEV, TRAIN Fold B or test read; any edit of the released store or its twin (both are
read-only and pinned by SHA-256 here); store version 2, which the delta-consumption table informs and which needs
its own registration; and any claim that Training-Free GRPO beats GEPA or ACE, whose arms reuse this store and
this supply route under their own registrations.

## 10. The coordinator's sequence

On the main checkout, after merging `fable/cell1reg`. Nothing below was performed by the registering agent.

**1. Mint the decision receipt** from the sealed ADV-1 receipt (WSL, from the study root):

```
python scripts/flights/batch/mint_decision_receipt.py \
  --from stage3-advantage-r01 --from-tag STAGE3-ADVANTAGE-R01 --from-date 2026-09-22 \
  --name stage3-delta-cell-r01 --tag STAGE3-DELTA-CELL-R01 --date 2026-09-22 \
  --expected-contacts 4424 --expected-gpu-hours 1.76 \
  --replace 'SAEA-SLURP-STAGE3-ADVANTAGE-R01-SMOKE-4-FIT-V1=SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-FIT-V1' \
  --replace 'SAEA-SLURP-STAGE3-ADVANTAGE-R01-SMOKE-4-V1=SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V1' \
  --replace 'SAEA-SLURP-STAGE3-ADVANTAGE-R01-FIT-V1=SAEA-SLURP-STAGE3-DELTA-CELL-R01-FIT-V1' \
  --replace 'SAEA-SLURP-STAGE3-ADVANTAGE-R01-V1=SAEA-SLURP-STAGE3-DELTA-CELL-R01-V1' \
  --replace 'attempt-slurp-native-stage3-delta-cell-r01-smoke-4-v1-generation-recovery=attempt-slurp-native-stage3-delta-cell-smoke-4-v1-generation' \
  --replace 'attempt-slurp-native-stage3-delta-cell-r01-smoke-4-v1-fit=attempt-slurp-native-stage3-delta-cell-smoke-4-v1-fit' \
  --replace 'slurp-native-stage3-delta-cell-r01-smoke-4-fit-v1=slurp-native-stage3-delta-cell-smoke-4-fit-v1' \
  --replace 'slurp-native-stage3-delta-cell-r01-smoke-4-v1=slurp-native-stage3-delta-cell-smoke-4-v1' \
  --replace 'slurp-native-stage3-advantage-smoke-4-baseline-v1=slurp-native-stage3-delta-cell-smoke-4-baseline-v1' \
  --replace 'slurp-native-stage3-advantage-baseline-v1=slurp-native-stage3-delta-cell-baseline-v1' \
  --replace '7c603857503faacbc40999d0dd939202ac141ba50aac3fb5e3594542931c46d7=61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6' \
  --replace '8cbdb0acece69a74145685ab1b6452d494ac86a82b6b18b260cec66d36264762=4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb' \
  --decision "<one sentence: what is admitted>" \
  --authority "<owner decisions 83 / 99 / 101 / 106; spec S3-6 and S3-4s>" \
  --claim-boundary "<TRAIN development numbers; the twin decides attribution, never admission; no DEV, Fold B or test read>"
```

The `--replace` pairs are applied **in order**, after the tool's own five id substitutions, and the longer id
always precedes the shorter one it contains.

**1b. The receipt still needs two fields the tool cannot set**, because the ADV-1 template names four run ids and
one population and this family has eight run ids and two populations. Before the flip, on the data root:

```
python - <<'PY'
import io, json
p = "$SPEECHRL_DATA_DIR/coordination/slurp-stage3-delta-cell-r01-v1/root-admission-v1.json"
d = json.load(io.open(p, encoding="utf-8"))
d["eligible_run_ids"] = [
    "SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V1", "SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-FIT-V1",
    "SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-TWIN-V1", "SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-TWIN-FIT-V1",
    "SAEA-SLURP-STAGE3-DELTA-CELL-R01-V1", "SAEA-SLURP-STAGE3-DELTA-CELL-R01-FIT-V1",
    "SAEA-SLURP-STAGE3-DELTA-CELL-TWIN-V1", "SAEA-SLURP-STAGE3-DELTA-CELL-TWIN-FIT-V1"]
d["budget"]["arm"].update({"generation_calls_cap": 11880, "fit_endpoint_calls_cap": 47520,
                           "repeated_speech_audio_seconds_cap": 33930, "gpu_hours_fit_inclusive_cap": 12.0,
                           "native_task_contract_calls_cap": 6480, "official_complete_score_jobs": 1,
                           "ceiling_note": "11 contacts per row = 1 + 2 x (3 + 1 + 1), the locked plan's own"})
d["budget"]["smoke"].update({"generation_calls_cap": 44, "fit_endpoint_calls_cap": 176,
                             "repeated_speech_audio_seconds_cap": 117, "gpu_hours_fit_inclusive_cap": 1.0,
                             "native_task_contract_calls_cap": 24, "official_complete_score_jobs": 0})
io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=2) + "\n")
PY
```

**Check after minting** that `decision_id` is `slurp-stage3-delta-cell-r01-admission-v1`, that `eligible_run_ids`
names exactly the eight ids above, that no `stage3-advantage` / `ADVANTAGE` / `7c603857` / `8cbdb0ac` substring
survives, and that `population` describes TRAIN Fold A 1,080 and the four-row smoke rather than the R01C
construction roster.

**2. Flip the four generation cells** -- smoke, twin smoke, arm, twin -- one cycle each, on the clean tree:

```
bash scripts/flights/batch/cell1_flip_all.sh
```

which drives `repin_loop_generic.sh` over `cell1_repin_smoke.sh`, `cell1_repin_twin_smoke.sh`,
`cell1_repin_arm.sh` and `cell1_repin_twin.sh`. Each pass re-pins with `scripts/flights/repin_cell.py
--set-ready`, commits, and re-runs until the freshly composed hashes and the registered documents agree. The two
fit cells of the arm fragment stay `held` -- they are spend identities, never flown as generation cells.

**3. Chain the flights** through the batch driver only (owner decision 77):

```
bash scripts/flights/batch/batch_chain_cell1.sh
```

Two steps: step 1 flies the generation smoke then the 1,080-row arm; step 2 flies the twin smoke then the
1,080-row twin. Expected rows 4 then 1,080 per step, `contacts_per_row` 4 (the realised figure; PLAN measured
4.0963), `ceiling_per_row` 11, tool-free, session `serving-slurp-native-candidate-five-train-a-np4-v1`. Each arm
opens only after its own smoke seals, and the twin never flies beside the arm.

**4. Read**, arm first, then the twin, with `scripts/analysis/plan_cell_read.py` as `analysis-recipe-v1.json`
records. **5. Countersign** the eight exposure rows as the flights consume them. Do not countersign before contact.
