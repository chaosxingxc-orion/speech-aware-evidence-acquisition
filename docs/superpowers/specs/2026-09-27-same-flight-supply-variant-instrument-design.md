# Same-flight supply-variant instrument: design

Author: design agent (Fable 5.1), 2026-09-27, branch `fable/svinst`. Status: DESIGN, no code. Authority: owner decision 172 (2026-09-27), which
re-authorises `supply_variants` as an engineering-base INSTRUMENT for (a) same-flight A/B reads and
(b) evidence-varied rollouts for the sealed-credit inner loop (`sealed-credit-system-policy-v1`).
VAR-2 as a MECHANISM stays closed. No model, server or GPU contact was made.

## 0. What already exists

Item E42 is merged:

- `rails/supply_variants.py::parse_supply_variants` parses `roles.solver.supply_variants` (2 to 8
  arms, delivering arm last and override-free, no identical override sets, no first-phase knob,
  fail-closed fit). Knobs are limited to `SUPPLY_VARIANT_KNOB_TAILS`:
  `phase_supply.<phase>.{k, fuse_coverage.m|c|top_l}` and `candidate_supply.<phase>.max_candidates`.
- `core/flight/runtime.py::FlightRuntime._supply_variant_binding` builds one router per arm over one
  composite snapshot; `rails/runner.py` resolves arms in `settle`, refuses a delivering arm that
  diverges from the row's own supply, and seals the receipt through
  `rails/native_episode_receipt.py::validate_supply_variant_receipt`.
- `core/bundle/outputs.py` has invariant **I7v** (`SUPPLY_VARIANT_INVARIANT`,
  `_verify_supply_variant_trace_binding`): every arm contact of every Solver visit binds to its
  trace pair, and the row identity to the final delivering-arm contact. Missing: per-arm scoring
  custody and a paired read over arm columns.
- `scripts/analysis/stage3_rollout_score.py::render_supply_variant_first_visit` renders one
  first-visit column per arm; `score_supply_variant_copies` scores each column once through
  `core/scoring_batch.py::score_complete_derived_copy`, binding parent bundle, roster, scorer and
  copy hash.
- `rails/candidate_semantic_supply.py` has no `supply_variants` reference; an arm reaches it only
  through the rebuilt router. `CandidateSemanticSupplySpec` refuses
  `max_candidates > DEFAULT_MAX_SLURP_CANDIDATES` (3) unless the projection policy is configurable.
  COMP-1 uses the fixed bounded policy, so on COMP-1 an arm can only lower `max_candidates`.

VAR-2 closed (`docs/results/2026-09-25-slurp-var2-closed-engineering-failure.md`): arm `exk10`
carried 40 cumulative items against `max_supplied_items` 38 on a revision visit, because the fit
bound covered one visit while arms fanned out on every visit.

## 1. Uses, phases and reach

**(a) Same-flight A/B read.** Two supply constructions answer the same row in one flight, read
paired per row. The estimand is the **Solver-local answer under that supply at the first Solver
visit**, not the delivered full-system answer: non-delivering arms never reach the Reviewer or
Planner.

**(b) Evidence-varied rollouts.** One sealed flight on a tuning roster carries K evidence
constructions per row at temperature 0 (owner decision 172: temperature sampling is exhausted,
90.5 % of rows keep one intent across five samples). It adds per-arm citation custody (section 5), makes no claim, and carries no twin.

**Phases** (Q1 ruling):

- **Phase 1 (this spec)** is the Solver-local column read with an in-flight twin arm. It can read
  cells whose variant is a knob tail OR a release swap (Coordinator amendment, 2026-09-28, section 2):
  slot-side and Solver-supply cells, namely **W4**, **W5** and the **citation contract** -- each of
  these three is a RELEASE SWAP (an alternative pinned release+snapshot of a named store), not a knob
  tail as this sentence originally scoped them; no cell in this program is read as a knob-tail variant
  as of this amendment.
- **Phase 2** is an episode-level fork for Perception-phase variants: K full episodes per row with
  their own A/A, which ROLL-AA does not measure. Phase 1 cannot read the **agreement term**
  (`w_agree`), the **contrast cards** or the **centroid key**: a first-phase selection is seeded
  once into the row's initial `QueryState` and refused by name (`parse_supply_variant_knob`,
  refusal 8), and `rank_weights`, `facet_source` and `query_source` are not knob tails. Until phase 2 has its own spec, those cells fly cross-flight with an in-chain replicate.

## 2. Runtime contract

**One row, K contacts, I7 intact.** The delivering arm is last and override-free, so its request is
the locked plan's request by construction. The row's identity hashes are the delivering
contact's; the delivered text is that response or its registered normaliser output (I7n; COMP-1 declares
`deliver_normaliser = saea-deliver-cited-answer-normalise-v3-v1`). No arm output enters the
delivered text or any later node. I7, I7n and I7v hold; no grouped commit exists (the bundle refuses
`supply_variants` beside `solver_group` in `_verify_outputs_trace_binding`).

**Arm visits.** Add `supply_variants.arm_visits`: `"every"` or `"first"`. The parser default stays
`"every"`, so existing forms stay byte-identical, but `"first"` is the **default for instrument
use**: every cell whose `measurement_design` is `same-flight-supply-variant` or
`offline-sealed-pool` must declare it (gate finding `arm-visits-not-first`). Reason: the VAR-2
failure above. Under `"first"`, arms fan out only at the first Solver visit, revisits contact the
delivering arm alone, and `max_supplied_items` bounds exactly one visit. Changes:

- *Ceiling* (`rails/native_episode_config.py`, the `per_revision` formula near line 1713):
  `ceiling = base_ceiling + (K − 1)`, K counting the twin. For COMP-1
  (`phase-native-candidates-review-revise-cited-v1`, `max_contacts` 11), K = 2 or 3 gives 12 or 13.
  Each value needs its own program id and fragment, because the loader asserts
  `program.max_contacts ==` the graph ceiling.
- *Receipt*: the `supply_variants` block is sealed from the **first** Solver visit (today: the
  final one). Schema `saea-supply-variant-arms-v2` adds `arm_visits` and `visit_index: 0`; readers
  accept v1 unchanged.
- *I7v* under v2: visit 0 carries K contacts in declared order, every later visit exactly one (the
  delivering arm's). The row identity binds to the final delivering contact, and the delivering
  arm's ids still form an ordered prefix of the final `QueryState.retrieved_value_ids`.

**Twin arm** (Q3 ruling). Every same-flight read carries an arm row with
`replicate_of: "<delivering arm id>"`: no overrides, resolves exactly the delivering arm's ids,
exempt from refusal 10 (identical override sets) and from the receipt rule "every non-delivering
arm resolves at least one knob". It is the delivering arm's greedy repeat in the same contact batch
(the ROLL-AA construction) and costs one extra Solver contact per row.

**Where the variant id lives.** In `NativeRoleContactContext.variant_arm_id`, reaching the trace
through the role custody document only (`reproduction/ojw/native_request.py`, the conditional
`variant_arm_id` key; not the wire payload, so a twin's wire bytes equal the delivering arm's); in
the outputs row `supply_variants.arms[].{arm_id, contact_id, resolved_knobs, supplied_value_ids}`;
in the render manifest `arm_order`; and in the derived score receipt `column_binding.arm_id`.

**Cost, exposure and budget.** The package declares the cost: `variant_cost.extra_contacts_per_row`
(K − 1, twin included) and `variant_cost.extra_audio_seconds` ((K − 1) × row audio, since every arm
re-sends the speech packet at the first visit); the gate checks both against the arm list. The
exposure ledger keeps one generation row per run id (`calls` counts every arm contact; notes state
K, `arm_visits`, ceiling); one READ row per registered read run id
covers every column contrast and is countersigned before any column score is opened
(`stage3_paired_read.py::run_package`). `planned_model_calls >= rows × ceiling`
(`rails/runner.py` near line 5481); planned audio likewise. The budget is run-cumulative
(`core/model/adapter.py`, `prior_actual_usage`), so a recovery plan covers prior durable spend
plus its own worst case.

**Fit gate.** `fit_estimate`'s four numbers are MEASURED on the cell's own `native_contact_fit`
pass at the new ceiling, never round placeholders as in VAR-2. The runtime `max_supplied_items`
refusal stays.

**Coordinator amendment (2026-09-28): the release-swap route.** Two extensions, both engineering
base, on top of everything above. `rails/supply_variants.py`'s docstring said an arm "never swaps a
component or repoints a release"; this amendment adds the ONE named exception.

- **Base field.** A base's `knowledge_stores.<store>` gains an optional `alternates` field: a list of
  zero or more `{release, snapshot}` pin pairs, each hash-pinned exactly like the primary (same
  `{relpath, sha256}` shape, same escape-the-data-root refusal). Absent, a store composes exactly as
  before this amendment (`rails/knowledge_stores.py::KnowledgeStore.alternates` defaults to `()`).
  Example:
  ```json
  "knowledge_stores": {
    "intent-boundaries": {
      "store_role": "intent-boundaries",
      "snapshot": {"relpath": "knowledge/intent-boundaries/snapshot.json", "sha256": "<64-hex>"},
      "release": {"relpath": "knowledge/intent-boundaries/release.json", "sha256": "<64-hex>"},
      "alternates": [
        {
          "release": {"relpath": "knowledge/intent-boundaries/w4-release.json", "sha256": "<64-hex>"},
          "snapshot": {"relpath": "knowledge/intent-boundaries/w4-snapshot.json", "sha256": "<64-hex>"}
        }
      ]
    }
  }
  ```
  An alternate's bytes are hash-verified with the same rigor as the primary only at the point some
  arm actually selects it (`rails/knowledge_stores.py::load_knowledge_store_binding`, re-run with the
  alternate's pins substituted for the primary's) -- declaring one that no arm ever selects costs no
  extra load at flight assembly. `rails/knowledge_stores.py::declared_alternate_release_relpaths`
  reads the raw, not-yet-loaded config for the by-name pre-check below.
- **Arm route.** An arm may ADDITIONALLY declare `release_swap`, disjoint from `overrides`, naming ONE
  store the fragment already declares and ONE alternate release by its relpath:
  ```json
  {"arm_id": "w4-alt", "max_supplied_items": 8,
   "release_swap": {"store_id": "intent-boundaries",
                     "release": "knowledge/intent-boundaries/w4-release.json"}}
  ```
  (`rails/supply_variants.py::SupplyVariantReleaseSwap`, `parse_supply_variant_release_swap`, wired
  into `parse_supply_variants` via a new `declared_alternate_relpaths` parameter that
  `rails/native_episode_config.py` derives from the base's own `knowledge_stores`.) The delivering arm
  A never carries one (refused, the same reason it carries no knob override); a twin (`replicate_of`)
  never carries one either, so its wire bytes stay byte-identical to A's under this extension; two arms
  naming the identical `{store_id, release}` are refused as the same "identical overrides" defect a
  duplicate knob set already is. An arm may never name a release absent from the named store's declared
  `alternates` -- refused by name, before any contact, with a message naming the store and its declared
  alternates.
- **Runtime.** `core/flight/runtime.py::FlightRuntime._supply_action_router` gains a `release_swap`
  parameter: when set, it repoints the named store's `release`/`snapshot` to the matched alternate
  before reloading the binding, and its ONE exception to "the reloaded composite snapshot must equal
  the flight's own" is that this ONE named store may legitimately differ, resolved to exactly the
  selected alternate; every OTHER store must still resolve to exactly the flight's own pins, or the
  router refuses. `_supply_variant_binding` passes each arm's own `release_swap` through.
- **Receipt (I7v binding extended).** The supply-variant receipt schema bumps
  `saea-supply-variant-arms-v2` to `-v3` (`rails/supply_variants.py`,
  `rails/native_episode_receipt.py::validate_supply_variant_receipt`): every arm row gains
  `release_swap` -- `null` absent one, else the declared `{store_id, release}` the arm consumed. A v1
  or v2 receipt still validates unchanged; the delivering arm and any twin must declare `release_swap:
  null`, exactly as they must resolve no knobs.
- **Identity.** `core/flight/runtime.py::FlightRuntime._phase_seed_inputs` already binds
  `config=self._composed.values` (which includes `knowledge_stores.<store>.alternates` verbatim) into
  `core/preparation.py::artifact_inputs`'s `config_sha256`; this amendment additionally adds an
  EXPLICIT `sources["knowledge_store_alternates"]` entry
  (`_knowledge_store_alternate_identity`), so a prepared artifact's identity is provably sensitive to
  an alternate's pins changing even under a future narrowing of what `config_sha256` covers. This file
  is identity-bound already (`sources["implementation"]["runtime"]` hashes its own bytes); that a merge
  here busts every prepared artifact's identity is accepted -- flipped cells fly from their flight
  commits, held cells re-pin at flip.

## 3. Outputs, scoring and the paired read

**Sealed per arm** (exists): contact id, request hash, response text hash, resolved knobs,
supplied value ids and count, under the row's `supply_variants`; the raw arm response stays in the
trace. Use (b) additionally needs per-arm `cited_value_ids` under `saea-solver-cited-answer-v1`,
derived by the renderer from the trace (section 5).

**Column rendering.** `render_supply_variant_first_visit` today parses raw arm text with
`reproduction.slurp_scoring.parse_slu_response`, while the delivered column goes through the
registered normaliser and the SLURP deliver projection; under the cited-answer contract the two
disagree, so an arm-vs-delivered contrast would partly measure the renderer. Every column, twin and delivering first visit included, goes through the delivered row's
normaliser (`core.base.DELIVERY_NORMALISERS`, the cited-answer normaliser) and projection, and the
render refuses on any failure of acceptance test AT1.

**Scoring.** Once per complete arm column through `score_complete_derived_copy` (refuses a partial
or duplicate column, binds the parent manifest hash), never sharded, serial under
`--mode supply-variants`. The delivered row's
score remains the sealed `<run>.scores.json`.

**Paired read** (`scripts/analysis/stage3_paired_read.py`). `ArmSpec` gains an optional `column`
(`arm_id`); `slurp_paired_roster_read.load_arm` with a column reads the derived score and its
receipt instead of `<run>.scores.json`; a pair is refused unless both columns carry the same
`parent_manifest_sha256` . In package mode `arms.arm`,
`arms.in_chain_replicate` and `arms.comparator` accept `{"run_id", "attempt_id", "column"}`:
`vs-aa` reads twin against delivering column; the gating pass reads treatment against delivering
column. The bar is |twin offset| + its half-width, the same law as the cross-flight in-chain A/A.
`--delivery` is skipped for column pairs (Perception records are shared).

**Resampling** (Q4 ruling): by row, cluster key `sample_id`, the programme's
standard; the reader refuses a column recipe whose `resampling.unit` is not `"row"`. The
utterance-level number (ROLL-3 whole-utterance bootstrap) is reported beside it and never gates.

**Claim ceiling** (Q6 ruling). A Solver-local effect never supports a system-level
claim. A package whose `measurement_design` is `same-flight-supply-variant` may claim only
`"nominated"`, never `"admitted"`: `stage3_paired_read.py` writes `nominated` where it would write
an admitting verdict for column pairs, and `flight_registration_check.py` refuses any other
declared claim (finding `variant-claim-not-nominated`). A nomination sends the composed policy to a
full-system read against an in-chain A/A (measurement instrument note, section 5, "fly only the
composed policy").

## 4. Isolation and registration

- **No gold at runtime.** Arms re-cap knobs over released, hash-pinned stores;
  `_supply_variant_binding` refuses a different snapshot.
- **Tuning and read rosters.** The hazard is the choice of knob values, made on tuning
  rollouts (use b), not store content. The tuning and read rosters are disjoint by recording
  and utterance id, and both exclude every knowledge-source id of the snapshot (the R01/R01C
  lesson: exclude the exemplar pool and every card's `source_support`).
- **Null.** The twin's paired difference is the read's own null (Q3). The ROLL-AA null (0.735 SLU,
  0.000 intent at n = 200, R01C, 9 of 18 scenarios) is roster-specific and a per-row SLU mean
  (`rails/supply_variants.py`'s docstring warns that per-row and pooled estimands differ), so it is only the provisional floor anchor.
- **Registration fields** (Q2 ruling): keep the existing key `measurement_design` in
  `stage3_measurement`, no field migration, and add the value `same-flight-supply-variant` to
  `FLOOR_TABLE`/`DESIGNS` in `scripts/checks/stage3_effect_floor_check.py` and to the design
  handling in `scripts/checks/flight_registration_check.py`. Its floor is the twin null on the same
  estimand, the ROLL-AA anchor provisional until then. Required beside it: `tuning_roster` and
  `read_roster` (roster receipt paths), `aa_arm_id` (the twin), `variant_cost`, and
  `claim: "nominated"`.
- **Gate findings** in `flight_registration_check.py::check_cell`: `variant-design-missing`
  (baseline declares `supply_variants` without this design or `offline-sealed-pool`),
  `read-roster-mismatch` (`read_roster` split identity is not the cell's population),
  `tuning-read-overlap`, `roster-knowledge-overlap` (either roster meets the snapshot's
  `source_sample_ids`), `aa-arm-missing` (no `replicate_of` arm on a same-flight read),
  `arm-visits-not-first`, `variant-cost-mismatch`, and `variant-claim-not-nominated`.
- **COMP-1 restriction** (Q5 ruling): accepted; arms may only lower
  `max_candidates`. A configurable projection policy for arms is a mechanism change and stays out
  of the instrument.

## 5. The inner-loop use

A use-(b) cell is a rollout on the tuning roster with K ≤ 8 evidence arms, `arm_visits: "first"`,
temperature 0, design `offline-sealed-pool`, `claims_benefit` false. After the seal:

1. **Score** each arm column once (section 3).
2. **Credit.** `analysis/citation_credit.py` tables the delivering Solver contact's `supplied`,
   `cited` and `cited_correct` per `value_id`; extend it to one table per arm (key
   `(arm_id, value_id)`), correctness from that arm column's official per-row score.
3. **Select offline** over the sealed pool at the offline floor, among flown arms only: arm effects
   are not additive, so an unflown combination is never scored offline.

The selected construction flies as the one treatment arm beside the delivering arm and its twin
on the read roster; at most it is `nominated`, and admission needs the full-system read against an
in-chain A/A under rule 3 (roughly 2.5 pp bar). A
composed policy that changes anything outside the knob tails (Perception, rank weights, prompts)
skips the column read and goes straight to that cross-flight read (phase 2 later).

## 6. What stays closed

VAR-2 the mechanism is any rule whose delivered answer or downstream node depends on more than one
arm (a merge over arm outputs, an arm output shown downstream, a per-row delivering arm). The
instrument's arms are only sealed and scored. Enforced by `native_episode_config` refusal 13 (arms beside
`samples >= 2`); the bundle's refusal of `supply_variants` beside `solver_group`; I7v's "output
identity is the final delivering arm contact"; a new runner assertion that Reviewer and Planner
inputs hash-bind only the delivering arm's response; and `stage3_effect_floor_check` requiring a
cell with `supply_variants` to declare `same-flight-supply-variant` or `offline-sealed-pool` and a
`stage3_algorithm` that is not a VAR-2 mechanism family.

## 7. Acceptance tests

- **AT1 column reproduction.** On every row with no revision visit, the delivering arm's rendered
  first-visit column text equals the sealed delivered `text` byte for byte; a mismatch refuses the
  render. Covered in
  `tests/unit/test_stage3_rollout_score.py` with a cited-answer fixture needing the normaliser.
- **AT2 twin wire identity.** The twin's wire payload equals the delivering arm's byte for byte.
- **AT3 revision cardinality.** Under `"first"`, a revision visit at maximum reachable cardinality
  contacts one arm and stays within `max_supplied_items`
  (`tests/unit/test_stage3_supply_variant_interleaving.py`).
- **AT4 same-parent refusal.** A column pair with differing `parent_manifest_sha256` is refused.
- **AT5 claim ceiling.** A column package never emits `admitted`; the gate refuses a declared claim
  other than `nominated`.
- **AT6 seal path.** A fake sealed run with arms, twin and I7n passes `verify_bundle`, column
  render, `score_complete_derived_copy` (stub scorer) and the column paired read (the
  grouped-commit lesson).

## 8. Implementation plan: two merge sets

**Merge set A: read side and gates.** Merges as soon as the current flip cycle has recorded its
flight commits; it touches no file whose hash enters `sources.implementation`.

1. `scripts/checks/stage3_effect_floor_check.py` (new design value) and
   `scripts/checks/flight_registration_check.py` (design value, required fields, eight findings);
   tests in `tests/unit/test_stage3_effect_floor_check.py` and
   `tests/unit/test_flight_registration_check.py`, one synthetic cell per finding.
2. `scripts/analysis/stage3_rollout_score.py` (normalised column render, AT1 self-check, per-arm
   `cited_value_ids` from the trace) and `analysis/citation_credit.py` (per-arm tables).
3. `scripts/analysis/stage3_paired_read.py` and `scripts/analysis/slurp_paired_roster_read.py`
   (column source, same-parent refusal, row resampling, `nominated` ceiling); AT4, AT5; keep
   `tests/unit/test_stage3_paired_read.py`'s no-extension byte-identity test green.

**Merge set B: runtime and rails.** Lands only at the next deliberate re-pin point, which the
coordinator names: these files' hashes enter every prepared artifact's `sources.implementation`, so
merging them makes every pinned ready cell fail "prepared artifact identity mismatch"; the re-pin
is a loop-form `scripts/flights/repin_cell.py` pass of every ready cell at the flight commit.

4. Twin arm: `rails/supply_variants.py`, `rails/native_episode_receipt.py`; AT2.
5. `arm_visits`: `rails/native_episode_config.py`, `rails/runner.py` (visit-0 fan-out and receipt,
   single-arm downstream assertion), `core/flight/runtime.py` (seal validation),
   `core/bundle/outputs.py` (I7v v2); fragments
   `configs/policy/phase-native-candidates-review-revise-cited-variants2first-v1.json` (ceiling 12)
   and `-variants3first-v1` (13) registered in `rails/controllers.py`; AT3, AT6.
6. Registration (coordinator): dry run, `native_contact_fit` at the new ceiling with measured
   `fit_estimate`, four-row smoke, first instrument read with its twin.

**Coordinator amendment (2026-09-28), added to merge set B** (section 2 has the full design):

7. Release-swap route: `rails/knowledge_stores.py` (`KnowledgeStoreAlternate`,
   `declared_alternate_release_relpaths`), `rails/supply_variants.py`
   (`SupplyVariantReleaseSwap`, `parse_supply_variant_release_swap`, receipt schema v3),
   `rails/native_episode_receipt.py` (v3 `release_swap` field), `rails/native_episode_config.py`
   (`declared_alternate_relpaths` wiring), `core/flight/runtime.py`
   (`_supply_action_router`'s `release_swap` parameter, `_supply_variant_binding`,
   `_knowledge_store_alternate_identity` in `_phase_seed_inputs`); tests in
   `tests/unit/test_knowledge_store_release_alternates.py` and the extended
   `tests/unit/test_stage3_supply_variant_interleaving.py`.
8. Two UNCITED program fragments, copies of `phase-native-candidates-review-revise-v1` with
   `arm_visits: "first"` ceilings per the same formula as item 5's cited pair:
   `configs/policy/phase-native-candidates-review-revise-variants2first-v1.json` (ceiling 12) and
   `-variants3first-v1` (13), registered in `rails/controllers.py` exactly like the cited variants
   fragments in item 5; the existing cited fragments and every existing config stay byte-identical.

No instrument cell registers before set B. Neither `kb_policy.py` nor
`candidate_semantic_supply.py` changes. Gates after each task in both sets: `pytest`,
`engineering_base_check.py`, `stage3_effect_floor_check.py`, `flight_registration_check.py`,
`stage3_algorithm_label_check.py`.

## 9. Open questions and coordinator rulings

- **Q1.** Perception-phase supply cannot be an arm; design an episode-level fork?
  *Coordinator ruling (2026-09-27):* two phases. Phase 1 (column read, in-flight twin) reads W4, W5
  and the citation contract; phase 2 (episode-level fork, own A/A) reads the agreement term, contrast
  cards and centroid key, and is specified after phase 1 reads one real cell (section 1).
- **Q2.** Keep `measurement_design` or migrate to `stage3_measurement.design`?
  *Coordinator ruling (2026-09-27):* keep `measurement_design`, add the value
  `same-flight-supply-variant`, no field migration.
- **Q3.** A twin on every read, or one twin-only flight per roster?
  *Coordinator ruling (2026-09-27):* a twin (`replicate_of`) on every same-flight read, one extra
  Solver contact per row, cost declared in the package; bar = |twin offset| + its half-width.
- **Q4.** Resample by row or utterance (ROLL-3: 1.56 pooled micro vs 1.19 per row)?
  *Coordinator ruling (2026-09-27):* by row (`sample_id`); the utterance-level number is reported
  beside it, never gating.
- **Q5.** Accept that COMP-1 arms can only lower `max_candidates`?
  *Coordinator ruling (2026-09-27):* accepted; a configurable projection for arms is a mechanism
  change outside the instrument.
- **Q6.** May a Solver-local effect qualify a system claim?
  *Coordinator ruling (2026-09-27):* never; it only nominates the composed policy for a full-system
  read against an in-chain A/A. A `same-flight-supply-variant` package may claim `nominated`, never
  `admitted` (gate-enforced, section 3).
