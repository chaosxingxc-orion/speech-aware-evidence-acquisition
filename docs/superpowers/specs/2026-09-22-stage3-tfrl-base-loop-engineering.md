# Stage 3, layer A: the training-free RL base loop -- engineering specification

Author: the coordinator (Fable 5.1). Date: 2026-09-22. Status: ENGINEERING SPEC for items S3-1 .. S3-6 (the owner's
Stage-3 goal: "the basic engineering base is set by the field's open-source training-free RL techniques"; decisions
80-83; design `docs/superpowers/specs/2026-09-21-slurp-stage3-training-free-rl-design.md`; interfaces verified by a
read-only scouting pass on 2026-09-22). Everything here is one-factor cells on the LOCKED v2.0 plan
(`configs/baseline/slurp-native-default-plan-lock-baseline-v1.json`), read against the sealed PLAN arm at the plan's own
null (h_SLU 1.2485 / h_intent 0.9943), flown only through the scheduled-task queue (decision 77). No contact is
authorised by this document.

## 0. The loop in the repository's own terms

```
iteration t = 1..3
  S3-1  ROSTER    (model-free)  ~800 construction rows, semantic-diversity draw, receipt        [once]
  S3-2  ROLL-t    (flight)      the locked plan with the Solver drawing N = 5 samples on the roster; ~2.5 GPU-h
  S3-3  SCORE-t   (model-free)  official per-sample scores on COPIES, best/worst pair per disagreeing row
  S3-4  ADV-t     (flight)      one contact per disagreeing row: the core states what distinguished best from worst; ~0.3 GPU-h
  S3-5  DELTA-t   (model-free)  curate the statements into an append-only, provenance-tagged delta store version t
  S3-6  CELL-t    (flight)      the locked plan + delta store t as ONE factor on TRAIN A, twin as the form control; ~3.6 GPU-h
        -> per-scenario frontier read decides which deltas survive into t+1 (decision 83)
```

Semantic advantage (Training-Free GRPO), reflect-on-the-trace with Pareto selection (GEPA), grow-and-refine deltas that
are appended, never rewritten (ACE). Survey: `wiki/survey/workbench/training-free-rl-2026-09-21/README.md` (umbrella).

## S3-1  Construction roster (decision 81)

- Generator `scripts/build_slurp_stage3_construction_roster.py` (model-free): pool = the 9,354 construction utterances
  of `docs/receipts/knowledge/slurp-kb-size-pool-annotated-exemplars.json` (the 2026-09-13 exclusion of TRAIN A, TRAIN B,
  DEV-1000) MINUS every utterance with a recording in `docs/receipts/rosters/slurp-dev-2000-v1.json` and
  `slurp-dev-2000-added-v1.json` (decision 81 bars DEV-2000; the exclusion list of
  `scripts/build_slurp_exemplar_pool_assets.py` `EXCLUDE_ROSTER_RELPATHS` does not carry them). Embeddings: the sealed
  `vectors/slurp-kus3/facet-vectors.jsonl` (sha256 5dfe7523..., dimension `content`, ids `facet:content:<utterance_id>`)
  loaded through `rails.phase_supply.load_sealed_vectors`. Draw: per scenario (18 strata, the stratum is on the KB
  snapshot's values, never gold) a farthest-point traversal seeded 20260922 -- first point random, then repeatedly the
  utterance farthest (cosine) from the selected set -- until 44 or 45 per scenario (800 total, natural rounding fixed
  in the receipt); one recording per utterance (the first by id). Receipt `docs/receipts/rosters/slurp-stage3-construction-r01.json`
  through `core.roster.freeze_roster`'s schema (`saea-roster-receipt-v1`, `roster_role: construction`, `split_role:
  discovery`, items with `stratum`, `utterance_id`, `sample_id`, `audio_seconds`, plus `draw_rank` and `min_cosine_to_selected`),
  a `disjointness_proof` against the six forbidden rosters, the split identity hash, and a `diversity_report` (mean pairwise
  cosine of the draw vs a seeded uniform draw of the same size). Runtime view `configs/dataset/slurp-speech-native-stage3-construction-r01.json`
  (the DEV-2000 view is the shape precedent). Speech packets: the construction recordings' featcache packets must be
  promoted like `DEV-2000-ADDED-promotion.json` (a registered `SAEA-SN-...-PREPROCESS` preparation; the ENCODE step is a
  tool contact, registered before it runs); speech-query vectors for the exemplar supply = a new alias export of the
  pool-side content vectors (they are already sealed for every TRAIN utterance: `query-vectors-speech-content-v1`'s
  parent), no encoder contact.

## S3-2  Rollout cell ROLL-t

- Fragment `configs/baseline/slurp-native-stage3-rollout-baseline-v1.json` = the locked PLAN fragment with exactly:
  `native_episode.roles.solver.samples = 5`, `decoding_overrides = {temperature: 0.7, seed_offset: 0}`,
  `commit = {policy: saea-commit-plurality-support-v1, min_support: 3, similarity_threshold: 0.8}` (the B2 v3 form),
  and `native_episode.deliver_normaliser` REMOVED (the loader refuses a grouped Solver together with the normaliser node,
  `rails/native_episode_config.py` 1203-1212; the v3 projection is applied at scoring instead, section S3-3), on the
  S3-1 roster and its packets / vectors. Contact ceiling = 1 + 5 + 3 + 1 (+ revision) per row; expected 8 contacts per row
  x 800 rows = 6,400 contacts, about 2.5 GPU hours at np4. Every sample is custodied in `solver_group` (I7g); the
  delivered answer is the plurality commit (not read for anything but custody).
- Cell package `docs/readiness/2026-09-2x-slurp-stage3-rollout-r01-v1/` in the PLAN package's form (plans registered +
  fresh, protocol, analysis recipe, README, preregistration), four-row smoke, ledger rows (generation + fit, run ids
  `SAEA-SLURP-STAGE3-ROLLOUT-R01-V1` / `-FIT-V1` / `-SMOKE-4-...`), campaign plan, `allowed_execution_stages`
  check/worker/campaign, readiness held until root mints the decision receipt. Iteration t > 1 re-uses the roster and
  adds the delta store of iteration t-1 to the rollout fragment (so later rollouts sample under the improved context).

## S3-3  Score on copies and pair selection

- CLI `scripts/analysis/stage3_rollout_score.py` (model-free; the `score_copy` idiom of
  `scripts/analysis/slurp_verifier_measurement.py` 280-306 and the per-sample rendering of
  `analysis/native_commit_replay.replay_row`): for every row and every sample, render the sample's answer, score the
  five rendered copies once with `slurp-slu-official-projected-v3-train` (projection v3 applied offline = the locked
  plan's delivery node), keep per-sample `scenario_action_exact`, `slu_f1_f1`, `slot_f1_exact_{tp,fp,fn}`; per row:
  the best and worst sample by (SLU-F1, intent) with deterministic tie-breaks, `disagreement = best - worst`, the
  group's mean and the delivered answer's score. Output `analysis/SAEA-SLURP-STAGE3-ROLLOUT-R01-SCORE-V1/` with
  `per_row.json` (ids, scores, sample indices; no text), `pairs.json` (rows with disagreement > 0, the two sample
  indices), a per-scenario coverage table, all sha256-pinned, `contacts {model:0,...,scorer: 5}`. Registered as a
  `model-free-check` ledger row. Gold enters only inside the registered scorer (construction rows: legal).

## S3-4  The semantic-advantage contact ADV-t

- One contact per disagreeing row (expected 300-500 rows). The contact sees: the row's speech (the same packet), the
  BEST and the WORST sample answers (model outputs, custodied bytes, rendered as two labelled answer lines), and the
  CONSTRUCTION GOLD (decision 82; the construction-proposer precedent). It answers with a fixed-form statement:
  ```
  DELTA-KIND: <one of: intent-boundary | slot-contract | exemplar-note>
  TARGET: <scenario_action or slot type the statement is about>
  STATEMENT: <one sentence, <= 40 words, stating what made the better answer better>
  ```
  parsed by a closed-form parser (line-keyed, like the primitive verdict; illegal -> retained, dropped at curation).
- Engineering: a new arm value `construction-advantage-text` registered beside `construction-proposer-text` in
  `core/flight/runtime.py` `ARM_VISIBLE_FIELDS` / `arm_shows_construction_targets` and gated by the same construction
  roster role (`contracts/gate_exposure._require_construction_role_for_visible_targets`); its per-row material
  (best / worst answers + gold) is rendered ONLY into the instruction (never receipted; identities and counts sealed as
  `construction_draws` does at runtime.py 10250-10258); a `phase-direct-only-v1`-style one-phase program
  `phase-stage3-advantage-v1` with `phase_material.advantage.instruction_template = probes/slurp_stage3_advantage_v1.txt`
  and `response_format_id = stage3-advantage-statement-v1` (registered in `rails/controllers.py`
  `register_response_formats_v1`). The rows and pairs come from S3-3's `pairs.json` (a prepared per-row material
  artifact, pinned by sha256, its identity binding the rollout run). Cell package as S3-2, run ids
  `SAEA-SLURP-STAGE3-ADVANTAGE-R01-V1`; about 0.3 GPU hours.
- Boundary: the runner's leakage rule (`_assert_agent_control_excludes_knowledge_payloads`) still applies -- the two
  answers are model outputs, not store text; gold is legal only under the construction arm; nothing of this contact
  reaches an evaluated row.

## S3-5  The delta store (ACE grow-and-refine)

- A NEW named store `stage3-deltas` (store_role `stage3-deltas`), built by a new builder id
  `saea-authored-stage3-deltas-v1` in `rails/semantic_knowledge_build.py` from an authored-rows JSON that S3-5's CLI
  writes: one row per SURVIVING statement with `value_id = delta:<iteration>:<sha256(statement)[:12]>`, `content` = the
  statement, `associated_facet_ids` = the scenario / intent facet it targets, `source_sample_ids` = the construction
  rows it came from, `provenance_refs` = `advantage:<run>:<row>:<best>:<worst>`; `task_target` = `DELTA-KIND:TARGET`.
  Version t's authored rows = version t-1's rows (verbatim, never edited) + the new rows; dedup = exact normalised
  text and near-duplicates by token Jaccard >= 0.8 against every earlier row (the later one is dropped, its provenance
  appended to the survivor's `provenance_refs`). Released through `core.semantic_knowledge_preparation` to
  `knowledge/slurp/semantic/stage3-deltas-v<t>/` with release / completion / snapshot and a release-pins document in
  the form of `docs/readiness/2026-09-17-slurp-semantic-store-release-pins-v2.json` (`predecessor`, `changed_value_ids`,
  `unchanged_value_count`, `binding_sha256`). CLI `scripts/build_slurp_stage3_delta_store.py` (model-free).
- Supply route: `context_supply` of the store router (`rails/knowledge_stores.py` `build_knowledge_store_supply`) to
  the Solver phase: every delta of the store whose `associated_facet_ids` intersect the row's Perception candidate
  intents (the same candidate-bound routing the slot-contracts store uses), capped at 8 per row by
  `prior_score` = the statement's disagreement mass. A derangement twin (`twin` = the same deltas attached to the wrong
  facets) is the form control, as the store twins of B1 / IDXT were.

## S3-6  The TRAIN A cell CELL-t and the frontier read

- One factor on the locked plan: `knowledge_stores.stage3-deltas` (version t) with its `context_supply`; comparator
  the sealed PLAN arm; margins the plan's own null; twin arm as the form control; frontier row (decision 75); per-scenario
  table in both weightings (decision 83: the per-scenario effect x prefilled-token frontier decides which deltas survive
  -- a delta whose target scenario shows a net harm beyond the null band is retired in version t+1, one whose scenario
  gains is kept, and the cost weight is the frontier slope). Read by `plan_cell_read.py` with its per-cell registered
  facts (item E34) plus a delta-consumption read: which deltas were supplied, per scenario, and the saves / harms on the
  rows that received each delta.
- Exit (the owner's goal): a CI95-proven official SLU-F1 gain against the sealed PLAN arm on TRAIN A, replicated on
  Fold B's single evaluation read (decision 29 order), with the frontier row beside it.

## Algorithm labels, decision 101

Owner decision 101 (2026-09-22, translated): *"in the Stage-3 experiment set-up, different experiments must explicitly
mark which training-free RL they use; you may explore several groups of training-free RL algorithms."* Layer A flies
three families on the SAME ROLL-1 rollouts and the SAME locked plan, so each cell must say which family it instantiates
and which loop operator it exercises -- otherwise the arms of a verdict table are distinguishable only by a run id.

Every Stage-3 cell therefore carries a top-level `stage3_algorithm` object in its EXPERIMENT fragment:

```json
"stage3_algorithm": {"id": "tfgrpo-semantic-advantage-v1", "operators_used": ["credit_assignment"], "note": "one sentence"}
```

The id resolves in `core.base.STAGE3_ALGORITHMS`, registered from
`src/speech_aware_evidence_acquisition/core/stage3_algorithms.py` (one Registry mechanism, like every other
config-declared component id), and `operators_used` is a subset of what that algorithm DEFINES. The registry today:

| id | family | status | operators the algorithm defines | citation |
| --- | --- | --- | --- | --- |
| `shared-rollout` | shared substrate | base-loop | rollout, scoring | this spec, S3-2 / S3-3 |
| `tfgrpo-semantic-advantage-v1` | Training-Free GRPO | base-loop | rollout, scoring, credit_assignment, update, context_application | arXiv:2510.08191 |
| `gepa-reflective-pareto-v1` | GEPA | planned | credit_assignment, update, selection | arXiv:2507.19457 |
| `ace-grow-refine-v1` | ACE | planned | update, selection, context_application | see design spec section 6 |
| `none` | none | not-applicable | (none; states its `reason`) | not applicable |

The gate is `python scripts/checks/stage3_algorithm_label_check.py`: a fragment is a Stage-3 cell when its stem or
`experiment_id` carries the token `stage3`, when its text names either Stage-3 spec, or when it is on the check's
explicit list; every such cell must carry a resolvable label. Labelled today: ROLL-1 and its smoke (`shared-rollout`,
rollout), ADV-1 (`tfgrpo-semantic-advantage-v1`, credit_assignment), CELL-1 and its twin/fit/smoke siblings
(`tfgrpo-semantic-advantage-v1`, update + context_application). Allowlisted in the check with their reason, because
their composed hashes are already pinned and this repository does not rewrite a registered plan out from under a
ledger row: R-PRIM and its smoke, and the S3-1 packet-promotion preparation -- all three wear `none` as prose in their
own readiness notes and leave the allowlist the next time they are re-pinned. The label is echoed into every verdict
table by the read drivers (`scripts/analysis/stage3_rollout_score.py`'s `pairs.json` / `per_row.json` header and
`scripts/analysis/slurp_paired_roster_read.py`'s `verdict.json`), resolved from the run id or given by
`--stage3-algorithm`; ledger rows minted for a Stage-3 cell from now on name the id in their note, and rows written
before decision 101 are never rewritten.

### The GEPA and ACE arms

Both reuse the substrate rather than rebuilding it: ROLL-1's custodied grouped samples (S3-2) and S3-3's per-sample
official scores, pairs and per-scenario coverage, with no new rollout and no new scoring job. GEPA replaces the
credit-assignment and update operators: instead of one per-row advantage statement, a reflective mutation of the
delta / instruction text is proposed from the execution traces of a scenario's rows, and survivors are chosen by the
per-scenario Pareto frontier over per-row scores (decision 83's frontier rule is already the selection operator, so
GEPA changes what is proposed, not how the frontier is read). ACE replaces the update operator only: a curator turns
the same reflector output into incremental delta items, de-duplicated against every earlier item by the S3-5 rule
(exact normalised text, then token Jaccard >= 0.8, provenance merged into the survivor), growing the playbook and
never rewriting a view. Both release through the SAME `stage3-deltas` store and the SAME `context_supply` route as
CELL-1, so `CELL-1-GEPA` (`SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-V1`, store `stage3-deltas-gepa-v1`) and `CELL-1-ACE`
(`SAEA-SLURP-STAGE3-DELTA-CELL-ACE-R01-V1`, store `stage3-deltas-ace-v1`) are one-factor arms on the locked plan
against the same sealed PLAN comparator, the same own null and the same derangement-twin form control as CELL-1 --
the three families differ in the delta store they release and in nothing else. Neither cell exists yet; registering
one is a package plus a fragment carrying its own `stage3_algorithm` label, not new wiring.

## Sequencing and budget

S3-1 (CPU, plus one registered ENCODE preparation for the construction packets, about 1.5 GPU-h once) -> ROLL-1
(2.5 GPU-h) -> S3-3 (CPU) -> ADV-1 (0.3 GPU-h) -> S3-5 (CPU) -> CELL-1 + twin (3.6 GPU-h) -> read -> iteration 2.
Per iteration about 6.5 GPU hours; three iterations about 20 GPU hours plus the one-time packet promotion. E37 (the
measurable Reviewer) and the decision-85 pruning cells fly before ROLL-1 so the plan under rollout is the plan that will
be locked at base lock v3. E36b's B9a v2 cell joins after CELL-1 as a layer-B improvement.

## Proof obligations (before any flight)

Roster generator tests (exclusions, stratum quotas, farthest-point determinism, disjointness proof); rollout fragment
diff proof (exactly the four Solver keys and the removed normaliser); scoring CLI on a synthetic five-sample outputs
file (the projection-v3 scorer sibling reproduces the sealed B2 v3 numbers on a copy); the advantage arm's gating test
(a non-construction roster refuses the arm; the receipt never carries the material); the statement parser tests;
delta-store builder tests (append-only, dedup rule, provenance merge, predecessor verbatim); the context-supply route
test (candidate-bound, cap 8, twin derangement); gates green.
